from __future__ import annotations

import copy
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any

from .accel import try_compile
from .base import FieldSpec
from .errors import ValidationError, add_location

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    # PEP 681 view. ``@dataclass_transform`` teaches type checkers (ty, pyright,
    # mypy) that ``@seared`` synthesises a dataclass, and ``field_specifiers``
    # lists the Field constructors so ``x: str = s.Str(...)`` is read as a field
    # (annotation drives the type; the ``.pyi`` stubs return ``Any`` so the
    # assignment is legal). ``default=`` / ``default_factory=`` are the names
    # PEP 681 keys required-vs-optional off, which is why they are the only
    # spelling (``missing=``, which a checker read as *required*, was removed in
    # 0.4.0).
    from typing import dataclass_transform, overload

    from seared.fields.bool_ import Bool
    from seared.fields.bytes_ import Bytes
    from seared.fields.date import Date
    from seared.fields.datetime_ import DateTime
    from seared.fields.decimal_ import Decimal
    from seared.fields.dict_ import Dict
    from seared.fields.enum_ import Enum
    from seared.fields.field import Field as _Field
    from seared.fields.float_ import Float
    from seared.fields.int_ import Int
    from seared.fields.ndarray import NDArray
    from seared.fields.pandas_ import PandasFrame
    from seared.fields.path import Path
    from seared.fields.polars_ import PolarsFrame
    from seared.fields.str_ import Str
    from seared.fields.t import T
    from seared.fields.time_ import Time
    from seared.fields.timedelta import TimeDelta
    from seared.fields.tuple_ import Tuple as _Tuple
    from seared.fields.union import Union
    from seared.fields.uuid_ import UUID

    from .errors import PathSegment

    @overload
    def seared[ClsT](cls: type[ClsT], /) -> type[ClsT]: ...
    @overload
    def seared[ClsT](
        *,
        slots: bool = ...,
        validate: bool = ...,
        accel: bool = ...,
    ) -> Callable[[type[ClsT]], type[ClsT]]: ...
    @dataclass_transform(
        kw_only_default=True,
        field_specifiers=(
            _Field,
            Bool,
            Bytes,
            Date,
            DateTime,
            Decimal,
            Dict,
            Enum,
            Float,
            Int,
            NDArray,
            PandasFrame,
            Path,
            PolarsFrame,
            Str,
            T,
            Time,
            TimeDelta,
            _Tuple,
            Union,
            UUID,
        ),
    )
    def seared(cls=None, *, slots=True, validate=True, accel=True): ...
else:

    def seared(
        cls: type | None = None,
        *,
        slots: bool = True,
        validate: bool = True,
        accel: bool = True,
    ) -> Any:
        """Decorator turning a class into a seared dataclass.

        Usable bare (``@s.seared``) or parameterised
        (``@s.seared(slots=False, validate=False)``).

        ``accel=False`` keeps the class on the pure-Python ``load`` / ``dump``
        even when an accelerator backend is installed (see
        ``seared._core.accel``); it is the per-class opt-out and always wins.
        """

        def decorate(c: type) -> type:
            return _build(c, slots=slots, validate=validate, accel=accel)

        if cls is None:
            return decorate
        return decorate(cls)


#: One field as the per-object paths (``load``, ``dump``, construction)
#: iterate it: ``(attr, wire, field)`` as an exact tuple. ``FieldSpec`` is a
#: ``NamedTuple``, and CPython only specialises ``for attr, wire, f in specs``
#: for exact tuples; unpacking the named tuples on every call cost about 5% of
#: both ``load`` and ``dump``. ``__seared_fields__`` keeps the ``FieldSpec``s.
type _HotSpec = tuple[str, str, Any]


def _build(cls: type, *, slots: bool, validate: bool, accel: bool = True) -> type:
    from seared.fields.field import Field  # local import avoids core<->field cycle

    # Sampled before ``dataclass()`` — with ``slots=True`` it returns a *new*
    # class, and it replaces ``__init__`` either way, so this is the only
    # moment the class as *written* is observable. The accelerator seam needs
    # it: a backend constructing via ``__new__`` would skip a hand-written one.
    custom_init = '__init__' in cls.__dict__

    cls = dataclass(cls, slots=slots)
    specs: list[FieldSpec] = []
    unwrap_specs: list[tuple[str, Any]] = []
    for f in fields(cls):
        default = f.default
        if isinstance(default, Field):
            wire = default.data_key or f.name
            specs.append(FieldSpec(f.name, wire, default))
            if _is_unwrap(default):
                unwrap_specs.append((f.name, default))
    # Multiple UNWRAP fields are allowed when their (tag_key, payload_key)
    # wire-key sets are disjoint — each Union can claim its own discriminator
    # + payload region without collisions. Single-UNWRAP-per-class was the
    # 0.1.8 constraint; 0.1.9 relaxes it to per-key-disjoint.
    if len(unwrap_specs) > 1:
        seen: dict[str, str] = {}  # wire-key → first-seen-attr
        for attr, f in unwrap_specs:
            for key_attr in ('tag_key', 'payload_key'):
                key = getattr(f, key_attr, None)
                if key is None:
                    continue
                if key in seen:
                    msg = (
                        f'{cls.__name__}: multiple UNWRAP fields share wire '
                        f'key {key!r} ({seen[key]} and {attr}); each Union '
                        f'must use distinct tag_key / payload_key strings'
                    )
                    raise TypeError(msg)
                seen[key] = attr
    specs_t: tuple[FieldSpec, ...] = tuple(specs)
    cls.__seared_fields__ = specs_t
    hot: tuple[_HotSpec, ...] = tuple((spec.attr, spec.wire, spec.field) for spec in specs_t)

    _wrap_init_replaces_field_defaults(cls, hot)

    # Optional compiled core. Returns None — and records why on
    # ``cls.__seared_accel__`` — whenever the class stays on the Python path,
    # which is every class when no backend is installed.
    compiled = try_compile(
        cls,
        specs_t,
        validate=validate,
        accel=accel,
        custom_init=custom_init,
    )
    if compiled is None:
        dump_fn = _make_dump(cls, hot, validate)
        load_fn = _make_load(cls, hot, validate)
    else:
        load_fn, dump_fn = compiled
    # Parameter names are API: they must match ``Seared.dump`` / ``Seared.load``
    # or a caller writing to the documented signature (``Cls.load(data=...)``)
    # gets a TypeError at runtime while type-checking clean.
    cls.dump = classmethod(lambda _c, obj, format='json': dump_fn(obj, format))
    cls.load = classmethod(lambda _c, data, format='json': load_fn(data, format))

    # Attach per-format codec methods (to_json/from_json/to_toml/...) once
    # at decorator time. Optional formats (TOML write, YAML, ...) raise
    # informative ImportError from inside the call when the extra is
    # missing — no import cost here for users who don't use those.
    from seared.formats import _attach_format_methods

    _attach_format_methods(cls)

    return cls


def _is_unwrap(f: Any) -> bool:
    return getattr(type(f), 'UNWRAP', False)


_MUTABLE_DEFAULT_TYPES = (list, dict, set, frozenset)


def _wrap_init_replaces_field_defaults(cls: type, specs: tuple[_HotSpec, ...]) -> None:
    """Replace Field-instance defaults with the field's resolved value.

    Wraps ``cls.__init__`` so the substitution happens on natural
    instantiation.

    Without this wrapper, ``Foo()`` (where ``x: Optional[int] = s.Int()``)
    would leave ``self.x`` as the ``Int`` metadata object instead of ``None``.

    For mutable ``default`` values (``list``, ``dict``, ``set``,
    ``frozenset``), each instance gets its own ``copy.deepcopy`` of the
    template — closes the classic Python shared-default footgun
    (``f: list = s.Int(many=True, default=[])`` would otherwise have
    every instance share the same list object). Deep copy ensures
    nested mutable structures (``default={'tags': []}``) are also
    isolated per-instance. ``default_factory=`` is the cleaner spelling.

    A ``__post_init__`` is wrapped too, to substitute first. The dataclass
    ``__init__`` calls the hook before it returns — before the ``__init__``
    wrapper gets to run — so without this a hook would read an omitted field
    as its (truthy) ``Field`` object, where ``load``, which resolves every
    omitted field before constructing, hands it the real default. Wrapped,
    the hook sees the same values on both paths.
    """
    # Resolved here, once per class: an import inside the fill would run on
    # every construction, and so on every ``load``, nested objects included.
    # Local, as in ``_build``, to avoid the core<->fields import cycle.
    from seared.fields.field import Field

    original_init = cls.__init__

    def __init__(self: Any, *args: Any, **kwargs: Any) -> None:  # noqa: N807
        original_init(self, *args, **kwargs)
        # ``_fill_defaults``, inlined: ``load`` constructs through here once
        # per object, and the extra call cost about 5% of ``load``. Keep the
        # two in step; the mutable-default and ``__post_init__`` tests cover
        # each copy.
        for attr, _, f in specs:
            v = getattr(self, attr, None)
            if isinstance(v, Field):
                if f.default_factory is not None:
                    default = f.default_factory()
                else:
                    default = f.default
                    if isinstance(default, _MUTABLE_DEFAULT_TYPES):
                        default = copy.deepcopy(default)
                object.__setattr__(self, attr, default)

    __init__.__qualname__ = f'{cls.__qualname__}.__init__'
    cls.__init__ = __init__  # ty: ignore[invalid-assignment]

    # Looked up on the instance by the generated ``__init__``, so replacing it
    # after ``dataclass()`` is seen, ``slots=True`` included. An inherited hook
    # is wrapped again here, with this class's specs, so it also sees the
    # subclass's own omitted fields resolved; the fill is idempotent.
    original_post_init = getattr(cls, '__post_init__', None)
    if original_post_init is None:
        return

    def __post_init__(self: Any, *args: Any) -> None:  # noqa: N807
        _fill_defaults(self, specs, Field)
        original_post_init(self, *args)  # ``*args`` carries any ``InitVar``s

    __post_init__.__qualname__ = f'{cls.__qualname__}.__post_init__'
    cls.__post_init__ = __post_init__  # ty: ignore[unresolved-attribute]


def _fill_defaults(obj: Any, specs: tuple[_HotSpec, ...], field_class: type[_Field]) -> None:
    """Replace each attribute still holding its ``Field`` with the resolved default.

    The ``__post_init__`` wrapper's fill; the ``__init__`` wrapper inlines the
    same loop. It imports nothing, since it runs per construction: the caller
    passes the ``Field`` class in, resolved once per class.
    """
    for attr, _, f in specs:
        v = getattr(obj, attr, None)
        if isinstance(v, field_class):
            if f.default_factory is not None:
                default = f.default_factory()
            else:
                default = f.default
                if isinstance(default, _MUTABLE_DEFAULT_TYPES):
                    default = copy.deepcopy(default)
            object.__setattr__(obj, attr, default)


def _make_dump(cls: type, specs: tuple[_HotSpec, ...], validate: bool) -> Callable:
    cls_name = cls.__name__

    def dump(obj: Any, format: str = 'json') -> dict[str, Any]:
        out: dict[str, Any] = {}
        for attr, wire, f in specs:
            if not f.dump:
                continue
            v = getattr(obj, attr, None)
            if v is None:
                # ``null`` only where it's a value; anywhere else ``None`` is
                # left out, which a ``load`` reads back the same way.
                if f.nullable:
                    out[wire] = None
                continue
            try:
                if _is_unwrap(f):
                    # UNWRAP field serializes to a dict that's merged at the top
                    # level of the parent's wire form (rather than nested under
                    # ``wire``). This is what makes {tag, payload} envelopes land
                    # as flat keys on the parent class's dump.
                    out.update(f.serialize(v, validate, format=format))
                else:
                    out[wire] = _apply(f, v, 'serialize', validate, format=format)
            except ValidationError as e:
                # A ``dump`` path names attributes: its input is the object.
                add_location(e, attr, cls_name=cls_name)
                raise
        return out

    return dump


def _make_load(cls: type, specs: tuple[_HotSpec, ...], validate: bool) -> Callable:  # noqa: C901 — one flat loop: a helper would cost a call per key
    cls_name = cls.__name__

    # Each failure gains its location as it passes back up through here: a
    # ``load`` path names wire keys, so it addresses the input the caller
    # holds. The ``try`` blocks cost nothing until something raises.
    def load(data: Any, format: str = 'json') -> Any:
        if not isinstance(data, dict):
            msg = f'expected dict, got {type(data).__name__}'
            raise ValidationError(msg, cls_name=cls_name)
        kwargs: dict[str, Any] = {}
        for attr, wire, f in specs:
            if _is_unwrap(f):
                kwargs[attr] = _load_envelope(f, data, validate, format, cls_name)
                continue
            if wire in data:
                v = data[wire]
                if v is not None:
                    try:
                        kwargs[attr] = _apply(f, v, 'deserialize', validate, format=format)
                    except ValidationError as e:
                        add_location(e, wire, cls_name=cls_name)
                        raise
                    continue
                if f.nullable:
                    kwargs[attr] = None
                    continue
            # Absent, or a ``null`` on a field that isn't nullable, which reads
            # the same: it can't satisfy ``required`` or displace a default.
            # Absent keys are the common case (``dump`` strips ``None``), so
            # they pay no ``null`` check.
            if f.required:
                msg = 'required key missing'
                raise ValidationError(msg, path=(wire,), cls_name=cls_name)
            kwargs[attr] = f.default if f.default_factory is None else f.default_factory()
        try:
            return cls(**kwargs)
        except ValidationError as e:
            # Raised by a ``__post_init__``: it is about the object as a whole.
            add_location(e, cls_name=cls_name)
            raise

    return load


def _load_envelope(f: Any, data: dict[str, Any], validate: bool, format: str, cls_name: str) -> Any:
    """Load an UNWRAP field (a ``Union`` envelope) from the parent's own wire dict.

    It consumes whatever keys it recognises, which are the parent's, so a
    failure gains the class but no segment here; a nested envelope adds its
    ``payload_key`` itself. Out of ``load``'s loop because only classes with a
    ``Union`` pay for the call.
    """
    try:
        return f.deserialize(data, validate, format=format)
    except ValidationError as e:
        add_location(e, cls_name=cls_name)
        raise


def _apply(f: Any, v: Any, op: str, validate: bool, *, format: str = 'json') -> Any:
    # ``v`` is never ``None``: ``load`` and ``dump`` settle a ``None`` first.
    method = getattr(f, op)
    if f.keyed:
        if validate and not isinstance(v, dict):
            msg = f'expected dict for keyed field, got {type(v).__name__}'
            raise ValidationError(msg)
        try:
            return {k: method(x, validate, format=format) for k, x in v.items()}
        except ValidationError as e:
            add_location(e, *_first_failure(v.items(), method, validate, format))
            raise
    if f.many:
        if validate and not isinstance(v, (list, tuple)):
            msg = f'expected list for many field, got {type(v).__name__}'
            raise ValidationError(msg)
        try:
            return [method(x, validate, format=format) for x in v]
        except ValidationError as e:
            add_location(e, *_first_failure(enumerate(v), method, validate, format))
            raise
    return method(v, validate, format=format)


def _first_failure(
    items: Iterable[tuple[PathSegment, Any]],
    method: Callable[..., Any],
    validate: bool,
    format: str,
) -> tuple[PathSegment, ...]:
    """The key or index of the first item ``method`` rejects, found once something has failed.

    The comprehensions in ``_apply`` stay plain because a ``try`` around each
    item would cost every call that succeeds; the location is only worth
    working out after one hasn't. Running ``method`` again is safe: seared's
    fields have no side effects (a nested class's ``__post_init__`` runs again,
    and must not have them either). ``()`` if nothing fails the second time.
    """
    for key, x in items:
        try:
            method(x, validate, format=format)
        except ValidationError:
            return (key,)
    return ()
