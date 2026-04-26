from __future__ import annotations

from dataclasses import dataclass
from enum import Enum as PEnum
from typing import Type

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Enum(Field):
    enum: Type[PEnum] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.enum is None:
            raise TypeError('Enum field requires enum=<EnumClass>')

    def serialize(self, value, validate: bool = True, **kwargs):
        if isinstance(value, self.enum):
            return value.value
        if validate:
            raise ValidationError(f'expected {self.enum.__name__}, got {type(value).__name__}')
        return value

    def deserialize(self, value, validate: bool = True, **kwargs):
        if isinstance(value, self.enum):
            return value
        sample_value = next(iter(self.enum)).value
        is_int_enum = isinstance(sample_value, int) and not isinstance(sample_value, bool)
        try:
            if is_int_enum:
                return self.enum(int(value))
            return self.enum(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(f'{value!r} is not a valid {self.enum.__name__}') from e
