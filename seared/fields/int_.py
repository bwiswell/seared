from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from seared._core.errors import ValidationError

from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Int(Field):
    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> int:
        """Python ``int`` → JSON integer (rejects ``bool``)."""
        if validate and (isinstance(value, bool) or not isinstance(value, int)):
            msg = f'expected int, got {type(value).__name__}'
            raise ValidationError(msg)
        return int(value)

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> int:
        """JSON integer, float, or numeric string → ``int`` (rejects ``bool``)."""
        if isinstance(value, bool):
            if validate:
                msg = 'expected int, got bool'
                raise ValidationError(msg)
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, (str, float)):
            try:
                return int(value)
            except (TypeError, ValueError) as e:
                msg = f'cannot deserialize {value!r} as int'
                raise ValidationError(msg) from e
        msg = f'cannot deserialize {value!r} as int'
        raise ValidationError(msg)
