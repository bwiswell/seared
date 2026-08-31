from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Any

from seared._core.errors import ValidationError

from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Time(Field):
    format: str | None = None

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> str:
        """``time`` → ISO-8601 string, or ``format``-formatted when set."""
        if not isinstance(value, time):
            if validate:
                msg = f'expected time, got {type(value).__name__}'
                raise ValidationError(msg)
            return str(value)
        if self.format is None:
            return value.isoformat()
        return value.strftime(self.format)

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> time:  # noqa: ARG002 — signature fixed by Field
        """ISO-8601 (or ``format``-formatted) string → ``time``."""
        if isinstance(value, time):
            return value
        if not isinstance(value, str):
            msg = f'expected str for Time, got {type(value).__name__}'
            raise ValidationError(msg)
        try:
            if self.format is None:
                return time.fromisoformat(value)
            return datetime.strptime(value, self.format).time()  # noqa: DTZ007 — the field's `format` owns tz handling
        except ValueError as e:
            msg = f'invalid time {value!r}'
            raise ValidationError(msg) from e
