from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from seared._core.errors import ValidationError

from .field import Field


class Tuple(Field):
    __slots__ = ('tuple_fields',)

    def __init__(  # noqa: PLR0913 — mirrors the full Field option set
        self,
        *fields: Field,
        default: tuple | None = None,
        default_factory: Callable[[], Any] | None = None,
        missing: tuple | None = None,
        data_key: str | None = None,
        keyed: bool = False,
        many: bool = False,
        required: bool = False,
        dump: bool = True,
        doc: str | None = None,
    ) -> None:
        """Bind the per-slot ``fields`` alongside the standard field options."""
        super().__init__(
            data_key=data_key,
            keyed=keyed,
            many=many,
            required=required,
            dump=dump,
            default=default,
            default_factory=default_factory,
            missing=missing,
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
        return tuple(f.serialize(v, validate) for f, v in zip(self.tuple_fields, value, strict=False))

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> tuple:
        """List/tuple → tuple, each slot through its own field."""
        if validate and not isinstance(value, (tuple, list)):
            msg = f'expected list/tuple, got {type(value).__name__}'
            raise ValidationError(msg)
        if validate and len(value) != len(self.tuple_fields):
            msg = f'tuple length mismatch: expected {len(self.tuple_fields)}, got {len(value)}'
            raise ValidationError(msg)
        return tuple(f.deserialize(v, validate) for f, v in zip(self.tuple_fields, value, strict=False))
