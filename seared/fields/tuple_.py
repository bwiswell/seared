from __future__ import annotations

from typing import Any, Callable, Optional

from .._core.errors import ValidationError
from .field import Field


class Tuple(Field):
    __slots__ = ('tuple_fields',)

    def __init__(
        self,
        *fields: Field,
        default: Optional[tuple] = None,
        default_factory: Optional[Callable[[], Any]] = None,
        missing: Optional[tuple] = None,
        data_key: Optional[str] = None,
        keyed: bool = False,
        many: bool = False,
        required: bool = False,
        dump: bool = True,
        doc: Optional[str] = None,
    ):
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

    def serialize(self, value, validate: bool = True, **kwargs) -> tuple:
        if validate and not isinstance(value, (tuple, list)):
            raise ValidationError(f'expected tuple, got {type(value).__name__}')
        if validate and len(value) != len(self.tuple_fields):
            raise ValidationError(
                f'tuple length mismatch: expected {len(self.tuple_fields)}, got {len(value)}'
            )
        return tuple(
            f.serialize(v, validate) for f, v in zip(self.tuple_fields, value)
        )

    def deserialize(self, value, validate: bool = True, **kwargs) -> tuple:
        if validate and not isinstance(value, (tuple, list)):
            raise ValidationError(f'expected list/tuple, got {type(value).__name__}')
        if validate and len(value) != len(self.tuple_fields):
            raise ValidationError(
                f'tuple length mismatch: expected {len(self.tuple_fields)}, got {len(value)}'
            )
        return tuple(
            f.deserialize(v, validate) for f, v in zip(self.tuple_fields, value)
        )
