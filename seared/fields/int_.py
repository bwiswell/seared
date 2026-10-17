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
        """JSON integer, integral float, or numeric string → ``int`` (rejects ``bool``).

        Lax mode also truncates a fractional float (``3.7`` → ``3``) and
        takes ``bool``; neither mode lets an ``OverflowError`` (``inf``) out.
        """
        if isinstance(value, bool):
            if validate:
                msg = 'expected int, got bool'
                raise ValidationError(msg)
            return int(value)
        if isinstance(value, int):
            return value
        n = coerce_int(value, validate)
        if n is None:
            msg = f'cannot deserialize {value!r} as int'
            raise ValidationError(msg)
        return n


def coerce_int(value: Any, validate: bool) -> int | None:
    """A float or numeric string as an ``int`` under ``Int``'s rules, or ``None`` if they refuse it.

    Strict mode refuses a float with a fractional part, where truncating would
    lose data; lax mode truncates. Numeric strings stay accepted in both,
    since string-only sources (topic captures) decode through here. ``nan``
    and ``inf`` are refused in both modes. Shared with an int-valued ``Enum``,
    which takes the same values as an ``Int``.
    """
    if isinstance(value, float):
        if validate and not value.is_integer():
            return None
    elif not isinstance(value, str):
        return None
    try:
        return int(value)
    except ValueError, OverflowError:
        return None
