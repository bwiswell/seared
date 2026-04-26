from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Date(Field):
    format: Optional[str] = None

    def serialize(self, value, validate: bool = True, **kwargs) -> str:
        if not isinstance(value, date):
            if validate:
                raise ValidationError(f'expected date, got {type(value).__name__}')
            return str(value)
        if self.format is None:
            return value.isoformat()
        return value.strftime(self.format)

    def deserialize(self, value, validate: bool = True, **kwargs) -> date:
        if isinstance(value, date):
            return value
        if not isinstance(value, str):
            raise ValidationError(f'expected str for Date, got {type(value).__name__}')
        try:
            if self.format is None:
                return date.fromisoformat(value)
            from datetime import datetime
            return datetime.strptime(value, self.format).date()
        except ValueError as e:
            raise ValidationError(f'invalid date {value!r}') from e
