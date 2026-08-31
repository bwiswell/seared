from __future__ import annotations

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any

from .errors import ValidationError

FieldSpec = tuple[str, str, Any]  # (attr_name, wire_key, Field instance)


if TYPE_CHECKING:
    from collections.abc import Callable

    # PEP 681 view. ``@dataclass_transform`` teaches type checkers (ty, pyright,
    # mypy) that ``@seared`` synthesises a dataclass, and ``field_specifiers``
    # lists the Field constructors so ``x: str = s.Str(...)`` is read as a field
    # (annotation drives the type; the ``.pyi`` stubs return ``Any`` so the
    # assignment is legal). ``default=`` / ``default_factory=`` are the names the
    # checker keys required/optional off — hence Option A in the plan.
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

    @overload
    def seared[ClsT](cls: type[ClsT], /) -> type[ClsT]: ...
    @overload
    def seared[ClsT](
        *,
        slots: bool = ...,
        validate: bool = ...,
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
    def seared(cls=None, *, slots=True, validate=True): ...
else:

    def seared(
        cls: type | None = None,
        *,
        slots: bool = True,
        validate: bool = True,
    ) -> Any:
        """Decorator turning a class into a seared dataclass.

        Usable bare (``@s.seared``) or parameterised
        (``@s.seared(slots=False, validate=False)``).
        """

        def decorate(c: type) -> type:
            return _build(c, slots=slots, validate=validate)

        if cls is None:
            return decorate
        return decorate(cls)


def _build(cls: type, *, slots: bool, validate: bool) -> type:
    from seared.fields.field import Field  # local import avoids core<->field cycle

    cls = dataclass(cls, slots=slots)
    specs: list[FieldSpec] = []
    unwrap_specs: list[tuple[str, Any]] = []
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

    _wrap_init_replaces_field_defaults(cls, specs_t)

    dump_fn = _make_dump(specs_t, validate)
    load_fn = _make_load(cls, specs_t, validate)
    cls.dump = classmethod(lambda _c, o, format='json': dump_fn(o, format))
    cls.load = classmethod(lambda _c, d, format='json': load_fn(d, format))

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


def _wrap_init_replaces_field_defaults(cls: type, specs: tuple[FieldSpec, ...]) -> None:
    """Replace Field-instance defaults with the field's resolved value.

    Wraps ``cls.__init__`` so the substitution happens on natural
    instantiation.

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

    from seared.fields.field import Field

    original_init = cls.__init__

    def __init__(self: Any, *args: Any, **kwargs: Any) -> None:  # noqa: N807
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
    cls.__init__ = __init__  # ty: ignore[invalid-assignment]


def _make_dump(specs: tuple[FieldSpec, ...], validate: bool) -> Callable:
    def dump(obj: Any, format: str = 'json') -> dict[str, Any]:
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


def _make_load(cls: type, specs: tuple[FieldSpec, ...], validate: bool) -> Callable:
    cls_name = cls.__name__

    def load(data: Any, format: str = 'json') -> Any:
        if not isinstance(data, dict):
            msg = f'{cls_name}.load expected dict, got {type(data).__name__}'
            raise ValidationError(msg)
        kwargs: dict[str, Any] = {}
        for attr, wire, f in specs:
            if _is_unwrap(f):
                # UNWRAP field consumes whatever wire keys it recognises from
                # the parent's payload — we pass the whole dict.
                kwargs[attr] = f.deserialize(data, validate, format=format)
                continue
            if wire in data:
                kwargs[attr] = _apply(
                    f,
                    data[wire],
                    'deserialize',
                    validate,
                    format=format,
                )
            elif f.required:
                msg = f'{cls_name}.{attr} is required'
                raise ValidationError(msg)
            elif f.default_factory is not None:
                kwargs[attr] = f.default_factory()
            else:
                kwargs[attr] = f.missing
        return cls(**kwargs)

    return load


def _apply(f: Any, v: Any, op: str, validate: bool, *, format: str = 'json') -> Any:
    method = getattr(f, op)
    if v is None:
        return None
    if f.keyed:
        if validate and not isinstance(v, dict):
            msg = f'expected dict for keyed field, got {type(v).__name__}'
            raise ValidationError(msg)
        return {k: method(x, validate, format=format) for k, x in v.items()}
    if f.many:
        if validate and not isinstance(v, (list, tuple)):
            msg = f'expected list for many field, got {type(v).__name__}'
            raise ValidationError(msg)
        return [method(x, validate, format=format) for x in v]
    return method(v, validate, format=format)
