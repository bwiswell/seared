from __future__ import annotations

from dataclasses import dataclass

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Str(Field):
    def serialize(self, value, validate: bool = True, **kwargs) -> str:
        if validate and not isinstance(value, str):
            raise ValidationError(f'expected str, got {type(value).__name__}')
        return str(value)

    def deserialize(self, value, validate: bool = True, **kwargs) -> str:
        if isinstance(value, str):
            return value
        if validate:
            raise ValidationError(f'expected str, got {type(value).__name__}')
        return str(value)
