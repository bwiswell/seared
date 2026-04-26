from __future__ import annotations

from dataclasses import dataclass

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Float(Field):
    def serialize(self, value, validate: bool = True, **kwargs) -> float:
        if validate:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValidationError(f'expected float, got {type(value).__name__}')
        return float(value)

    def deserialize(self, value, validate: bool = True, **kwargs) -> float:
        if isinstance(value, bool):
            if validate:
                raise ValidationError('expected float, got bool')
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError as e:
                raise ValidationError(f'cannot deserialize {value!r} as float') from e
        raise ValidationError(f'cannot deserialize {value!r} as float')
