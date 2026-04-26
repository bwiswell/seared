from __future__ import annotations

from dataclasses import dataclass

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Dict(Field):
    def serialize(self, value, validate: bool = True, **kwargs) -> dict:
        if validate and not isinstance(value, dict):
            raise ValidationError(f'expected dict, got {type(value).__name__}')
        return dict(value)

    def deserialize(self, value, validate: bool = True, **kwargs) -> dict:
        if validate and not isinstance(value, dict):
            raise ValidationError(f'expected dict, got {type(value).__name__}')
        return dict(value)
