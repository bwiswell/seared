from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from seared._core.errors import ValidationError

from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class TimeDelta(Field):
    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> float:
        """``timedelta`` → total seconds as a JSON number."""
        if isinstance(value, timedelta):
            return value.total_seconds()
        if validate:
            msg = f'expected timedelta, got {type(value).__name__}'
            raise ValidationError(msg)
        return float(value)

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> timedelta:  # noqa: ARG002 — signature fixed by Field
        """Seconds (number or numeric string) → ``timedelta``."""
        if isinstance(value, timedelta):
            return value
        try:
            return timedelta(seconds=float(value))
        except (TypeError, ValueError) as e:
            msg = f'cannot deserialize {value!r} as timedelta'
            raise ValidationError(msg) from e
