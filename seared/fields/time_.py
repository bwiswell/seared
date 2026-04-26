from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Time(Field):
    format: Optional[str] = None

    def serialize(self, value, validate: bool = True, **kwargs) -> str:
        if not isinstance(value, time):
            if validate:
                raise ValidationError(f'expected time, got {type(value).__name__}')
            return str(value)
        if self.format is None:
            return value.isoformat()
        return value.strftime(self.format)

    def deserialize(self, value, validate: bool = True, **kwargs) -> time:
        if isinstance(value, time):
            return value
        if not isinstance(value, str):
            raise ValidationError(f'expected str for Time, got {type(value).__name__}')
        try:
            if self.format is None:
                return time.fromisoformat(value)
            return datetime.strptime(value, self.format).time()
        except ValueError as e:
            raise ValidationError(f'invalid time {value!r}') from e
