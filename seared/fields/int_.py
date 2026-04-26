from __future__ import annotations

from dataclasses import dataclass

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Int(Field):
    def serialize(self, value, validate: bool = True, **kwargs) -> int:
        if validate:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(f'expected int, got {type(value).__name__}')
        return int(value)

    def deserialize(self, value, validate: bool = True, **kwargs) -> int:
        if isinstance(value, bool):
            if validate:
                raise ValidationError('expected int, got bool')
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, (str, float)):
            try:
                return int(value)
            except (TypeError, ValueError) as e:
                raise ValidationError(f'cannot deserialize {value!r} as int') from e
        raise ValidationError(f'cannot deserialize {value!r} as int')
