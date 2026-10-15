from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from seared._core.errors import ValidationError

from .field import Field

_TRUE = frozenset({'true', '1', 'yes', 'on'})
_FALSE = frozenset({'false', '0', 'no', 'off'})


@dataclass(frozen=True, kw_only=True, slots=True)
class Bool(Field):
    def serialize(self, value: bool, validate: bool = True, **kwargs: Any) -> bool:
        """Python ``bool`` → JSON boolean."""
        if validate and not isinstance(value, bool):
            msg = f'expected bool, got {type(value).__name__}'
            raise ValidationError(msg)
        return bool(value)

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> bool:
        """JSON boolean → ``bool``, coercing the usual string and int spellings.

        Lax mode reads the same spellings first and only then falls back to
        truthiness, so ``'false'`` is ``False`` in both modes. Lax still never
        raises: anything else is its truthiness (``'maybe'`` → ``True``).
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            low = value.strip().lower()
            if low in _TRUE:
                return True
            if low in _FALSE:
                return False
        if not validate:
            return bool(value)
        if isinstance(value, int):
            return bool(value)
        msg = f'cannot deserialize {value!r} as bool'
        raise ValidationError(msg)
