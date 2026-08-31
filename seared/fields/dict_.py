from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from seared._core.errors import ValidationError

from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Dict(Field):
    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> dict:
        """Python ``dict`` → JSON object (shallow copy; values pass through)."""
        if validate and not isinstance(value, dict):
            msg = f'expected dict, got {type(value).__name__}'
            raise ValidationError(msg)
        return dict(value)

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> dict:
        """JSON object → ``dict`` (shallow copy; values pass through)."""
        if validate and not isinstance(value, dict):
            msg = f'expected dict, got {type(value).__name__}'
            raise ValidationError(msg)
        return dict(value)
