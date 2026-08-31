from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass
from typing import Any

from seared._core.errors import ValidationError

from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class UUID(Field):
    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> str:
        """``uuid.UUID`` → its canonical hyphenated string."""
        if isinstance(value, _uuid.UUID):
            return str(value)
        if validate:
            msg = f'expected UUID, got {type(value).__name__}'
            raise ValidationError(msg)
        return str(value)

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> _uuid.UUID:  # noqa: ARG002 — signature fixed by Field
        """Canonical UUID string → ``uuid.UUID``."""
        if isinstance(value, _uuid.UUID):
            return value
        if isinstance(value, str):
            try:
                return _uuid.UUID(value)
            except ValueError as e:
                msg = f'invalid UUID: {value!r}'
                raise ValidationError(msg) from e
        msg = f'cannot deserialize {value!r} as UUID'
        raise ValidationError(msg)
