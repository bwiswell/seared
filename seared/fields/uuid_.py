from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class UUID(Field):
    def serialize(self, value, validate: bool = True, **kwargs) -> str:
        if isinstance(value, _uuid.UUID):
            return str(value)
        if validate:
            raise ValidationError(f'expected UUID, got {type(value).__name__}')
        return str(value)

    def deserialize(self, value, validate: bool = True, **kwargs) -> _uuid.UUID:
        if isinstance(value, _uuid.UUID):
            return value
        if isinstance(value, str):
            try:
                return _uuid.UUID(value)
            except ValueError as e:
                raise ValidationError(f'invalid UUID: {value!r}') from e
        raise ValidationError(f'cannot deserialize {value!r} as UUID')
