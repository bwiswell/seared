from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class DateTime(Field):
    format: Optional[str] = None

    def serialize(self, value, validate: bool = True, **kwargs) -> str:
        if not isinstance(value, datetime):
            if validate:
                raise ValidationError(f'expected datetime, got {type(value).__name__}')
            return str(value)
        if self.format is None:
            return value.isoformat()
        return value.strftime(self.format)

    def deserialize(self, value, validate: bool = True, **kwargs) -> datetime:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            raise ValidationError(f'expected str for DateTime, got {type(value).__name__}')
        try:
            if self.format is None:
                return datetime.fromisoformat(value)
            return datetime.strptime(value, self.format)
        except ValueError as e:
            raise ValidationError(f'invalid datetime {value!r}') from e
