from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from seared._core.errors import ValidationError, add_location

from .field import Field
from .kind import FieldKind


class Tuple(Field):
    KIND = FieldKind.TUPLE

    __slots__ = ('tuple_fields',)

    def __init__(  # noqa: PLR0913 — mirrors the full Field option set
        self,
        *fields: Field,
        default: tuple | None = None,
        default_factory: Callable[[], Any] | None = None,
        data_key: str | None = None,
        keyed: bool = False,
        many: bool = False,
        required: bool = False,
        nullable: bool = False,
        dump: bool = True,
        doc: str | None = None,
    ) -> None:
        """Bind the per-slot ``fields`` alongside the standard field options."""
        super().__init__(
            data_key=data_key,
            keyed=keyed,
            many=many,
            required=required,
            nullable=nullable,
            dump=dump,
            default=default,
            default_factory=default_factory,
            doc=doc,
        )
        object.__setattr__(self, 'tuple_fields', fields)

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> tuple:
        """Fixed-arity tuple → tuple, each slot through its own field."""
        if validate and not isinstance(value, (tuple, list)):
            msg = f'expected tuple, got {type(value).__name__}'
            raise ValidationError(msg)
        if validate and len(value) != len(self.tuple_fields):
            msg = f'tuple length mismatch: expected {len(self.tuple_fields)}, got {len(value)}'
            raise ValidationError(msg)
        return self._each(value, 'serialize', validate, kwargs)

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> tuple:
        """List/tuple → tuple, each slot through its own field."""
        if validate and not isinstance(value, (tuple, list)):
            msg = f'expected list/tuple, got {type(value).__name__}'
            raise ValidationError(msg)
        if validate and len(value) != len(self.tuple_fields):
            msg = f'tuple length mismatch: expected {len(self.tuple_fields)}, got {len(value)}'
            raise ValidationError(msg)
        return self._each(value, 'deserialize', validate, kwargs)

    def _each(self, value: Any, op: str, validate: bool, hints: dict[str, Any]) -> tuple:
        """Each slot through its own field; a failure gains the slot's index.

        The codec hints (``format=``) go to every slot, as ``T`` passes them to
        its nested class: without them a ``Bytes`` slot stayed base64 under
        ``format='msgpack'`` while a top-level one went native.
        """
        out = []
        for i, (f, v) in enumerate(zip(self.tuple_fields, value, strict=False)):
            try:
                out.append(getattr(f, op)(v, validate, **hints))
            except ValidationError as e:
                add_location(e, i)
                raise
        return tuple(out)
