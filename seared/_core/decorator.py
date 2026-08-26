from __future__ import annotations

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any, Callable, Tuple

from .errors import ValidationError


FieldSpec = Tuple[str, str, Any]  # (attr_name, wire_key, Field instance)


if TYPE_CHECKING:
    # PEP 681 view. ``@dataclass_transform`` teaches type checkers (ty, pyright,
    # mypy) that ``@seared`` synthesises a dataclass, and ``field_specifiers``
    # lists the Field constructors so ``x: str = s.Str(...)`` is read as a field
    # (annotation drives the type; the ``.pyi`` stubs return ``Any`` so the
    # assignment is legal). ``default=`` / ``default_factory=`` are the names the
    # checker keys required/optional off — hence Option A in the plan.
    from typing import TypeVar, dataclass_transform, overload

    from ..fields.bool_ import Bool
    from ..fields.bytes_ import Bytes
    from ..fields.date import Date
    from ..fields.datetime_ import DateTime
    from ..fields.decimal_ import Decimal
    from ..fields.dict_ import Dict
    from ..fields.enum_ import Enum
    from ..fields.field import Field as _Field
    from ..fields.float_ import Float
    from ..fields.int_ import Int
    from ..fields.ndarray import NDArray
    from ..fields.pandas_ import PandasFrame
    from ..fields.path import Path
    from ..fields.polars_ import PolarsFrame
    from ..fields.str_ import Str
    from ..fields.t import T
    from ..fields.time_ import Time
    from ..fields.timedelta import TimeDelta
    from ..fields.tuple_ import Tuple as _Tuple
    from ..fields.union import Union
    from ..fields.uuid_ import UUID

    _T = TypeVar('_T')

    @overload
    def seared(cls: type[_T], /) -> type[_T]: ...
    @overload
    def seared(
        *, slots: bool = ..., validate: bool = ...,
    ) -> Callable[[type[_T]], type[_T]]: ...
    @dataclass_transform(
        kw_only_default=True,
        field_specifiers=(
            _Field, Bool, Bytes, Date, DateTime, Decimal, Dict, Enum, Float,
            Int, NDArray, PandasFrame, Path, PolarsFrame, Str, T, Time,
            TimeDelta, _Tuple, Union, UUID,
        ),
    )
    def seared(cls=None, *, slots=True, validate=True): ...
else:
    def seared(cls=None, *, slots: bool = True, validate: bool = True):
        """Decorator turning a class into a seared dataclass.

        Usable bare (``@s.seared``) or parameterised
        (``@s.seared(slots=False, validate=False)``).
        """
        def decorate(c):
            return _build(c, slots=slots, validate=validate)
        if cls is None:
            return decorate
        return decorate(cls)


def _build(cls, *, slots: bool, validate: bool):
    from ..fields.field import Field  # local import avoids core<->field cycle
    cls = dataclass(cls, slots=slots)
    specs: list[FieldSpec] = []
    unwrap_specs: list[Tuple[str, Any]] = []
    for f in fields(cls):
        default = f.default
        if isinstance(default, Field):
            wire = default.data_key or f.name
            specs.append((f.name, wire, default))
            if _is_unwrap(default):
                unwrap_specs.append((f.name, default))
    # Multiple UNWRAP fields are allowed when their (tag_key, payload_key)
    # wire-key sets are disjoint — each Union can claim its own discriminator
    # + payload region without collisions. Single-UNWRAP-per-class was the
    # 0.1.8 constraint; 0.1.9 relaxes it to per-key-disjoint.
    if len(unwrap_specs) > 1:
        seen: dict[str, str] = {}     # wire-key → first-seen-attr
        for attr, f in unwrap_specs:
            for key_attr in ('tag_key', 'payload_key'):
                key = getattr(f, key_attr, None)
                if key is None:
                    continue
                if key in seen:
                    raise TypeError(
                        f'{cls.__name__}: multiple UNWRAP fields share wire '
                        f'key {key!r} ({seen[key]} and {attr}); each Union '
                        f'must use distinct tag_key / payload_key strings'
                    )
                seen[key] = attr
    specs_t: Tuple[FieldSpec, ...] = tuple(specs)
    cls.__seared_fields__ = specs_t

    _wrap_init_replaces_field_defaults(cls, specs_t)

    dump_fn = _make_dump(cls, specs_t, validate)
    load_fn = _make_load(cls, specs_t, validate)
    cls.dump = classmethod(lambda _c, o, format='json': dump_fn(o, format))
    cls.load = classmethod(lambda _c, d, format='json': load_fn(d, format))

    # Attach per-format codec methods (to_json/from_json/to_toml/...) once
    # at decorator time. Optional formats (TOML write, YAML, ...) raise
    # informative ImportError from inside the call when the extra is
    # missing — no import cost here for users who don't use those.
    from ..formats import _attach_format_methods
    _attach_format_methods(cls)

    return cls


def _is_unwrap(f) -> bool:
    return getattr(type(f), 'UNWRAP', False)


_MUTABLE_DEFAULT_TYPES = (list, dict, set, frozenset)


def _wrap_init_replaces_field_defaults(cls, specs: Tuple[FieldSpec, ...]) -> None:
    """Wrap ``cls.__init__`` so Field-instance defaults are replaced with the
    field's ``missing`` value on natural instantiation.

    Without this wrapper, ``Foo()`` (where ``x: Optional[int] = s.Int()``)
    would leave ``self.x`` as the ``Int`` metadata object instead of ``None``.

    For mutable ``missing`` values (``list``, ``dict``, ``set``,
    ``frozenset``), each instance gets its own ``copy.deepcopy`` of the
    template — closes the classic Python shared-default footgun
    (``f: list = s.Int(many=True, missing=[])`` would otherwise have
    every instance share the same list object). Deep copy ensures
    nested mutable structures (``missing={'tags': []}``) are also
    isolated per-instance.
    """
    import copy as _copy
    from ..fields.field import Field

    original_init = cls.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        for attr, _, f in specs:
            v = getattr(self, attr, None)
            if isinstance(v, Field):
                if f.default_factory is not None:
                    missing = f.default_factory()
                else:
                    missing = f.missing
                    if isinstance(missing, _MUTABLE_DEFAULT_TYPES):
                        missing = _copy.deepcopy(missing)
                object.__setattr__(self, attr, missing)

    __init__.__qualname__ = f'{cls.__qualname__}.__init__'
    cls.__init__ = __init__


def _make_dump(cls, specs: Tuple[FieldSpec, ...], validate: bool) -> Callable:
    def dump(obj, format: str = 'json') -> dict[str, Any]:
        out: dict[str, Any] = {}
        for attr, wire, f in specs:
            if not f.dump:
                continue
            v = getattr(obj, attr, None)
            if v is None:
                continue
            if _is_unwrap(f):
                # UNWRAP field serializes to a dict that's merged at the top
                # level of the parent's wire form (rather than nested under
                # ``wire``). This is what makes {tag, payload} envelopes land
                # as flat keys on the parent class's dump.
                out.update(f.serialize(v, validate, format=format))
            else:
                out[wire] = _apply(f, v, 'serialize', validate, format=format)
        return out
    return dump


def _make_load(cls, specs: Tuple[FieldSpec, ...], validate: bool) -> Callable:
    cls_name = cls.__name__

    def load(data, format: str = 'json') -> Any:
        if not isinstance(data, dict):
            raise ValidationError(f'{cls_name}.load expected dict, got {type(data).__name__}')
        kwargs: dict[str, Any] = {}
        for attr, wire, f in specs:
            if _is_unwrap(f):
                # UNWRAP field consumes whatever wire keys it recognises from
                # the parent's payload — we pass the whole dict.
                kwargs[attr] = f.deserialize(data, validate, format=format)
                continue
            if wire in data:
                kwargs[attr] = _apply(
                    f, data[wire], 'deserialize', validate, format=format,
                )
            elif f.required:
                raise ValidationError(f'{cls_name}.{attr} is required')
            elif f.default_factory is not None:
                kwargs[attr] = f.default_factory()
            else:
                kwargs[attr] = f.missing
        return cls(**kwargs)
    return load


def _apply(f, v: Any, op: str, validate: bool, *, format: str = 'json') -> Any:
    method = getattr(f, op)
    if v is None:
        return None
    if f.keyed:
        if validate and not isinstance(v, dict):
            raise ValidationError(f'expected dict for keyed field, got {type(v).__name__}')
        return {k: method(x, validate, format=format) for k, x in v.items()}
    if f.many:
        if validate and not isinstance(v, (list, tuple)):
            raise ValidationError(f'expected list for many field, got {type(v).__name__}')
        return [method(x, validate, format=format) for x in v]
    return method(v, validate, format=format)
