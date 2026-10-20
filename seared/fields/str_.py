from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from seared._core.errors import ValidationError

# ``StrChecks`` at runtime: ``_checks``'s annotation names it, and
# ``typing.get_type_hints`` evaluates that (0.4.3).
from .constraints import StrChecks, check_default, check_string, string_checks
from .field import Field
from .kind import FieldKind


@dataclass(frozen=True, kw_only=True, slots=True)
class Str(Field):
    KIND = FieldKind.STR

    # Lengths (0.4.4), in code points, and a pattern, JSON Schema's: an
    # ECMA-262 regex within the subset Python reads the same way, searched for.
    # Checked on a strict load and dump (``seared.fields.constraints``).
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    # The checks, reduced once at declaration, or ``None``.
    _checks: StrChecks | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Reduce the checks to one record, refusing a declaration they can't hold."""
        super().__post_init__()
        checks = string_checks(self)
        object.__setattr__(self, '_checks', checks)
        if checks is not None:
            check_default(self, lambda value: check_string(value, checks))

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> str:
        """Python ``str`` → JSON string, passing its checks."""
        # The common case first, and without the slower checks: an exact
        # ``str`` on an unchecked field is its own wire form.
        if type(value) is str and self._checks is None:
            return value
        if validate and not isinstance(value, str):
            msg = f'expected str, got {type(value).__name__}'
            raise ValidationError(msg)
        text = str(value)
        if self._checks is not None and validate:
            check_string(text, self._checks)
        return text

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> str:
        """JSON string → ``str``; strict mode then runs its checks."""
        if type(value) is str and self._checks is None:
            return value
        if isinstance(value, str):
            text = value
        elif validate:
            msg = f'expected str, got {type(value).__name__}'
            raise ValidationError(msg)
        else:
            text = str(value)
        if self._checks is not None and validate:
            check_string(text, self._checks)
        return text
