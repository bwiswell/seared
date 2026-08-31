from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from seared._core.errors import ValidationError

from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Str(Field):
    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> str:
        """Python ``str`` → JSON string."""
        if validate and not isinstance(value, str):
            msg = f'expected str, got {type(value).__name__}'
            raise ValidationError(msg)
        return str(value)

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> str:
        """JSON string → ``str``."""
        if isinstance(value, str):
            return value
        if validate:
            msg = f'expected str, got {type(value).__name__}'
            raise ValidationError(msg)
        return str(value)
