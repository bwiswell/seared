"""The accelerator seam — optional compiled ``load`` / ``dump``.

seared's Python implementation is canonical and always present. When an
accelerator backend (``rusted``) is installed *and* a class is built entirely
from seared-native fields that backend supports, ``@seared`` swaps its
generated closures for the backend's compiled equivalents. Everything else
falls back — silently, and by design.

Four rules keep that safe:

1. **seared owns the knowledge of seared.** This module walks
   ``__seared_fields__`` and emits a plain-data spec; a backend never
   introspects a ``Field``. The spec shape is versioned by :data:`SPEC_ABI`
   and a backend must declare the same integer or it is not used.
2. **Exact type identity gates acceleration.** A subclass of ``s.Int`` may
   override ``deserialize``, so ``isinstance`` is unsound here — only the
   exact classes in :func:`_kinds` are accelerable.
3. **Per class, all or nothing.** A class is accelerated only if every field
   is supported, recursively through ``T``. A backend is never asked to call
   back into Python for a field it doesn't understand.
4. **A backend can only ever be a no-op.** Anything unexpected — missing
   module, ABI mismatch, a backend that raises — records a reason and falls
   back to the Python path. The only exception is ``SEARED_ACCEL=require``,
   which exists so CI can assert the backend actually loaded.

Costs nothing when no backend is installed: the spec is never emitted, and
the module-level imports here are stdlib-only.

Environment:

- ``SEARED_ACCEL`` — ``auto`` (default) / ``off`` / ``require``.
- ``SEARED_ACCEL_BACKEND`` — module to import instead of ``rusted``. The
  test suite points this at its pure-Python reference core.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cache
from importlib import import_module
from typing import TYPE_CHECKING, Any

from .errors import SearedError, ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from seared.fields.field import Field

#: Version of the spec shape handed to a backend. A backend declares the
#: ``SPEC_ABI`` it was built against; only an exact match is used. This is
#: the whole compatibility gate — seared is zero-dependency and has no PEP
#: 440 specifier parser available, so version *strings* are diagnostic only.
SPEC_ABI = 1

#: Backend module imported when ``SEARED_ACCEL_BACKEND`` is unset.
DEFAULT_BACKEND = 'rusted'

MODE_ENV = 'SEARED_ACCEL'
BACKEND_ENV = 'SEARED_ACCEL_BACKEND'

_MODES = frozenset({'auto', 'off', 'require'})

#: Stands in for the backend triple under ``SEARED_ACCEL=off``, which never
#: imports a backend at all. Annotated so ``off`` doesn't widen ``mod``.
_OFF: tuple[Any, str, str | None] = (None, '', None)


@dataclass(frozen=True, slots=True)
class AccelInfo:
    """Whether a class got a compiled core, and if not, why not.

    Recorded on every ``@seared`` class as ``__seared_accel__``, alongside
    the ``__seared_fields__`` introspection surface.
    """

    accelerated: bool
    backend: str | None = None
    reason: str | None = None


class _NotAccelerableError(Exception):
    """Internal — carries the human-readable reason a class was declined."""


def _mode() -> str:
    """Read and validate ``SEARED_ACCEL``.

    Raises:
        SearedError: if the variable is set to anything unrecognised. A typo
            that silently disabled acceleration would defeat the point of
            having a ``require`` mode at all.
    """
    mode = os.environ.get(MODE_ENV, 'auto').strip().lower()
    if mode not in _MODES:
        msg = f'{MODE_ENV} must be one of {sorted(_MODES)}, got {mode!r}'
        raise SearedError(msg)
    return mode


@cache
def _backend() -> tuple[Any, str, str | None]:
    """Import and vet the backend once.

    Returns:
        ``(module, name, decline_reason)``. The name is the *configured* one
        and is always present, so diagnostics can always name what was tried.
    """
    name = os.environ.get(BACKEND_ENV, '').strip() or DEFAULT_BACKEND
    try:
        mod = import_module(name)
    except ImportError:
        return None, name, f'accelerator backend {name!r} is not installed'
    abi = getattr(mod, 'SPEC_ABI', None)
    if abi != SPEC_ABI:
        return None, name, (f'accelerator backend {name!r} declares SPEC_ABI {abi!r}; this seared emits {SPEC_ABI}')
    if not callable(getattr(mod, 'compile_spec', None)):
        return None, name, f'accelerator backend {name!r} has no compile_spec()'
    return mod, name, None


def _reset() -> None:
    """Drop the cached backend lookup. For tests that flip the env vars."""
    _backend.cache_clear()


@cache
def _kinds() -> dict[Any, str]:
    """Exact field class → spec kind name.

    Two groups, in the order accelerator backends implement them: the
    scalars plus nested ``T`` — cheap to coerce, and where the large speedups
    live — then the parse-and-construct types (``UUID``, the date-likes,
    ``Decimal``, ``Bytes``, ...), whose cost is dominated by building the
    Python object either way. A backend may implement only the first group; it
    declines the rest by name, and the class keeps the Python path.

    Imported lazily: ``_core`` must not import ``fields`` at module load.

    Still absent, and each for a reason: ``Union`` (an UNWRAP field consuming
    multiple keys from the *parent's* map), ``Tuple`` (per-slot sub-fields),
    and the ``NDArray`` / DataFrame fields (optional imports, and dominated by
    frame conversion anyway).
    """
    from seared.fields.bool_ import Bool
    from seared.fields.bytes_ import Bytes
    from seared.fields.date import Date
    from seared.fields.datetime_ import DateTime
    from seared.fields.decimal_ import Decimal
    from seared.fields.dict_ import Dict
    from seared.fields.enum_ import Enum
    from seared.fields.float_ import Float
    from seared.fields.int_ import Int
    from seared.fields.path import Path
    from seared.fields.str_ import Str
    from seared.fields.t import T
    from seared.fields.time_ import Time
    from seared.fields.timedelta import TimeDelta
    from seared.fields.uuid_ import UUID

    return {
        # Tier 1
        Int: 'int',
        Float: 'float',
        Str: 'str',
        Bool: 'bool',
        T: 'nested',
        # Tier 2 — parse-and-construct
        UUID: 'uuid',
        Date: 'date',
        DateTime: 'datetime',
        Time: 'time',
        TimeDelta: 'timedelta',
        Decimal: 'decimal',
        Bytes: 'bytes',
        Enum: 'enum',
        Path: 'path',
        Dict: 'dict',
    }


#: Per-kind configuration a backend needs beyond the universal flags, as
#: attribute names read off the ``Field``. User-supplied classes (an enum, a
#: concrete path type) and per-field options travel here; how to *use* them is
#: the backend's business.
#:
#: Adding a kind is additive and needs no :data:`SPEC_ABI` bump: a backend
#: that predates one declines it by name, before it ever looks for the config.
#: Changing the shape of an *existing* field spec is what would need the bump.
_KIND_CONFIG: dict[str, tuple[str, ...]] = {
    'bytes': ('encoding',),
    'date': ('format',),
    'datetime': ('format',),
    'time': ('format',),
    'decimal': ('as_number',),
    'enum': ('enum',),
    'path': ('concrete',),
}


def _nested_spec(cls: Any) -> dict[str, Any]:
    """The already-emitted spec of a nested ``T(cls)`` target.

    Reuses ``cls.__seared_spec__`` rather than re-deriving. A nested class is
    necessarily decorated *before* the class referencing it, so its spec (or
    its decline reason) is already recorded — which is also why no cycle
    guard is needed: a schema cycle cannot be constructed at decoration time.
    """
    spec = getattr(cls, '__seared_spec__', None)
    if spec is not None:
        return spec
    info = getattr(cls, '__seared_accel__', None)
    name = getattr(cls, '__name__', repr(cls))
    reason = info.reason if info is not None else f'{name} is not a @seared class'
    raise _NotAccelerableError(reason)


def _field_spec(owner: str, attr: str, wire: str, f: Field) -> dict[str, Any]:
    """Emit one field's plain-data spec, or decline the whole class."""
    kind = _kinds().get(type(f))
    if kind is None:
        msg = f'{owner}.{attr}: {type(f).__name__} is not an accelerated field type'
        raise _NotAccelerableError(msg)
    spec: dict[str, Any] = {
        'attr': attr,
        'wire': wire,
        'kind': kind,
        'required': f.required,
        'many': f.many,
        'keyed': f.keyed,
        'dump': f.dump,
        # ``missing`` is the resolved default — ``Field.__post_init__`` has
        # already folded ``default=`` into it, so a backend never reimplements
        # that resolution.
        'default': f.missing,
        'default_factory': f.default_factory,
    }
    if kind == 'nested':
        try:
            spec['schema'] = _nested_spec(f.schema)  # ty: ignore[unresolved-attribute]
        except _NotAccelerableError as exc:
            msg = f'{owner}.{attr} → {exc}'
            raise _NotAccelerableError(msg) from exc
    for option in _KIND_CONFIG.get(kind, ()):
        spec[option] = getattr(f, option)
    return spec


def _class_spec(cls: type, specs: tuple[tuple[str, str, Any], ...], validate: bool) -> dict[str, Any]:
    """Emit the whole-class spec handed to a backend's ``compile_spec``."""
    name = cls.__name__
    return {
        'abi': SPEC_ABI,
        'cls': cls,
        'name': name,
        'validate': validate,
        # The exception class to raise, carried as data. A backend must raise
        # *seared's* ValidationError or a caller's ``except s.ValidationError``
        # would stop catching it — and a backend that imported seared to get it
        # would no longer be the dependency-free leaf the design rests on.
        'error': ValidationError,
        'fields': [_field_spec(name, attr, wire, f) for attr, wire, f in specs],
    }


def _decline(cls: type, reason: str | None) -> None:
    """Record why ``cls`` keeps the Python path, and return no callables."""
    cls.__seared_accel__ = AccelInfo(accelerated=False, reason=reason)  # ty: ignore[unresolved-attribute]


def _blocked(cls: type, *, mode: str, accel: bool, unavailable: str | None, custom_init: bool) -> str | None:
    """The reason ``cls`` can't be handed to a backend at all, or ``None``.

    Ordered by precedence: the env var beats the per-class opt-out, which
    beats availability, which beats the construction-path gates.
    ``unavailable`` is non-``None`` exactly when no backend loaded.
    """
    if mode == 'off':
        return f'{MODE_ENV}=off'
    if not accel:
        return 'accel=False on the decorator'
    if unavailable is not None:
        return unavailable
    # Both of these are bypassed by the ``__new__`` + slot assignment a
    # compiled core constructs through, so they are not accelerable.
    if custom_init:
        return 'class defines its own __init__'
    if hasattr(cls, '__post_init__'):
        return 'class defines __post_init__'
    return None


def try_compile(
    cls: type,
    specs: tuple[tuple[str, str, Any], ...],
    *,
    validate: bool,
    accel: bool,
    custom_init: bool,
) -> tuple[Callable[..., Any], Callable[..., Any]] | None:
    """Compile ``cls``'s ``load`` / ``dump`` through the accelerator backend.

    Records the outcome on ``cls.__seared_accel__`` either way, and the
    emitted spec on ``cls.__seared_spec__`` when compilation succeeds (a
    class referencing this one as ``T(cls)`` reads it back).

    Args:
        cls: The class being built, already through ``dataclasses.dataclass``.
        specs: The ``(attr, wire_key, Field)`` triples from the decorator.
        validate: The class's strict/lax flag.
        accel: The decorator's per-class ``accel=`` opt-out.
        custom_init: Whether the class as *written* defined its own
            ``__init__``. Must be sampled before ``dataclass()`` replaces it.

    Returns:
        The ``(load, dump)`` pair, or ``None`` when the class keeps the
        Python path.

    Raises:
        SearedError: only under ``SEARED_ACCEL=require``, and only when no
            backend could be loaded at all. A class declining on its own
            merits is a normal outcome in every mode — seared's own suite is
            full of classes no Tier-1 backend can accelerate.
    """
    mode = _mode()
    # ``off`` never even imports the backend.
    mod, backend_name, unavailable = _OFF if mode == 'off' else _backend()
    if mode == 'require' and mod is None:
        msg = f'{MODE_ENV}=require, but {unavailable}'
        raise SearedError(msg)

    blocked = _blocked(cls, mode=mode, accel=accel, unavailable=unavailable, custom_init=custom_init)
    if blocked is not None:
        return _decline(cls, blocked)

    try:
        spec = _class_spec(cls, specs, validate)
    except _NotAccelerableError as exc:
        return _decline(cls, str(exc))

    try:
        compiled = mod.compile_spec(spec)
    except Exception as exc:  # noqa: BLE001 — a backend bug must never break decoration
        return _decline(cls, f'backend {backend_name!r} raised on compile_spec: {exc}')
    if compiled is None:
        return _decline(cls, f'backend {backend_name!r} declined the spec')

    load_fn, dump_fn = compiled
    cls.__seared_spec__ = spec  # ty: ignore[unresolved-attribute]
    cls.__seared_accel__ = AccelInfo(accelerated=True, backend=backend_name)  # ty: ignore[unresolved-attribute]
    return load_fn, dump_fn


def accel_status() -> dict[str, Any]:
    """Report the accelerator's global state.

    The per-class answer lives on each class as ``__seared_accel__`` (an
    :class:`AccelInfo`, whose ``reason`` names the field that blocked it).
    This is the other half: whether a backend loaded at all, and if not why.

    Returns:
        A plain dict — ``mode``, ``spec_abi``, ``available``, ``backend``,
        ``backend_version``, ``supports_seared``, ``reason``.
    """
    mod, backend_name, unavailable = _backend()
    return {
        'mode': _mode(),
        'spec_abi': SPEC_ABI,
        'available': mod is not None,
        'backend': None if mod is None else backend_name,
        'backend_version': None if mod is None else getattr(mod, '__version__', None),
        # Diagnostic only — never enforced. SPEC_ABI is the gate.
        'supports_seared': None if mod is None else getattr(mod, 'SUPPORTS_SEARED', None),
        'reason': unavailable,
    }


__all__ = ['SPEC_ABI', 'AccelInfo', 'accel_status', 'try_compile']
