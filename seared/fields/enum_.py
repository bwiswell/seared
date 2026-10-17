from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from enum import Enum as PEnum

from seared._core.errors import ValidationError

from .field import Field
from .int_ import coerce_int


@dataclass(frozen=True, kw_only=True, slots=True)
class Enum(Field):
    enum: type[PEnum]

    def __post_init__(self) -> None:
        """Reject a field declared without its ``enum=`` class."""
        super().__post_init__()
        if self.enum is None:
            msg = 'Enum field requires enum=<EnumClass>'
            raise TypeError(msg)

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:
        """Enum member → its ``.value``."""
        if isinstance(value, self.enum):
            return value.value
        if validate:
            msg = f'expected {self.enum.__name__}, got {type(value).__name__}'
            raise ValidationError(msg)
        return value

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:
        """Enum value (int- or str-valued) → the enum member.

        An int-valued enum takes the values an ``Int`` would, by the same
        mode's rules: strict refuses ``True`` and ``2.9``, which lax reads as
        ``1`` and ``2``.
        """
        if isinstance(value, self.enum):
            return value
        sample_value = next(iter(self.enum)).value
        is_int_enum = isinstance(sample_value, int) and not isinstance(sample_value, bool)
        if is_int_enum:
            key = _int_key(value, validate)
            if key is None:
                msg = f'{value!r} is not a valid {self.enum.__name__}'
                raise ValidationError(msg)
        else:
            key = value
        try:
            return self.enum(key)
        except (ValueError, TypeError) as e:
            msg = f'{value!r} is not a valid {self.enum.__name__}'
            raise ValidationError(msg) from e


def _int_key(value: Any, validate: bool) -> int | None:
    """An int-valued enum's lookup key, under ``Int``'s rules, or ``None`` if they refuse ``value``."""
    if isinstance(value, bool):
        return None if validate else int(value)
    if isinstance(value, int):
        return value
    return coerce_int(value, validate)
