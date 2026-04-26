from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class TimeDelta(Field):
    def serialize(self, value, validate: bool = True, **kwargs) -> float:
        if isinstance(value, timedelta):
            return value.total_seconds()
        if validate:
            raise ValidationError(f'expected timedelta, got {type(value).__name__}')
        return float(value)

    def deserialize(self, value, validate: bool = True, **kwargs) -> timedelta:
        if isinstance(value, timedelta):
            return value
        try:
            return timedelta(seconds=float(value))
        except (TypeError, ValueError) as e:
            raise ValidationError(f'cannot deserialize {value!r} as timedelta') from e
