from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from enum import Enum as PEnum

from seared._core.errors import ValidationError

from .field import Field


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

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:  # noqa: ARG002 — signature fixed by Field
        """Enum value (int- or str-valued) → the enum member."""
        if isinstance(value, self.enum):
            return value
        sample_value = next(iter(self.enum)).value
        is_int_enum = isinstance(sample_value, int) and not isinstance(sample_value, bool)
        try:
            if is_int_enum:
                return self.enum(int(value))
            return self.enum(value)
        except (ValueError, TypeError) as e:
            msg = f'{value!r} is not a valid {self.enum.__name__}'
            raise ValidationError(msg) from e
