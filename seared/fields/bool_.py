from __future__ import annotations

from dataclasses import dataclass

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Bool(Field):
    def serialize(self, value: bool, validate: bool = True, **kwargs) -> bool:
        if validate and not isinstance(value, bool):
            raise ValidationError(f'expected bool, got {type(value).__name__}')
        return bool(value)

    def deserialize(self, value, validate: bool = True, **kwargs) -> bool:
        if isinstance(value, bool):
            return value
        if not validate:
            return bool(value)
        if isinstance(value, str):
            low = value.strip().lower()
            if low in ('true', '1', 'yes', 'on'):
                return True
            if low in ('false', '0', 'no', 'off'):
                return False
        if isinstance(value, int):
            return bool(value)
        raise ValidationError(f'cannot deserialize {value!r} as bool')
