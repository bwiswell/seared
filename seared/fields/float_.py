from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from seared._core.errors import ValidationError

from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Float(Field):
    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> float:
        """Python ``float`` / ``int`` → JSON number (rejects ``bool``)."""
        if validate and (isinstance(value, bool) or not isinstance(value, (int, float))):
            msg = f'expected float, got {type(value).__name__}'
            raise ValidationError(msg)
        return float(value)

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> float:
        """JSON number or numeric string → ``float`` (rejects ``bool``)."""
        if isinstance(value, bool):
            if validate:
                msg = 'expected float, got bool'
                raise ValidationError(msg)
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError as e:
                msg = f'cannot deserialize {value!r} as float'
                raise ValidationError(msg) from e
        msg = f'cannot deserialize {value!r} as float'
        raise ValidationError(msg)
