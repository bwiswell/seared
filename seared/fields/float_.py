from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from seared._core.errors import ValidationError

# ``Bound`` at runtime: ``_bounds``'s annotation names it, and
# ``typing.get_type_hints`` evaluates that (0.4.3).
from .constraints import Bound, check_bounds, check_default, number_bounds
from .field import Field
from .kind import FieldKind


@dataclass(frozen=True, kw_only=True, slots=True)
class Float(Field):
    KIND = FieldKind.FLOAT

    # Bounds (0.4.4): at most one lower and one upper, each a finite number,
    # checked on a strict load and dump (``seared.fields.constraints``). A
    # bounded field refuses ``NaN``.
    ge: float | None = None
    gt: float | None = None
    le: float | None = None
    lt: float | None = None
    # The bounds, reduced once at declaration, or ``None``.
    _bounds: tuple[Bound, ...] | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Reduce the bounds to one check, refusing a declaration they can't hold."""
        super().__post_init__()
        bounds = number_bounds(self, integral=False)
        object.__setattr__(self, '_bounds', bounds)
        if bounds is not None:
            check_default(self, lambda value: check_bounds(value, bounds))

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> float:
        """Python ``float`` / ``int`` → JSON number (rejects ``bool``), within its bounds."""
        # The common cases first, and without the slower checks: an exact
        # ``float`` on an unbounded field is its own wire form, and an exact
        # ``int`` only needs converting.
        if self._bounds is None:
            kind = type(value)
            if kind is float:
                return value
            if kind is int:
                return float(value)
        if validate and (isinstance(value, bool) or not isinstance(value, (int, float))):
            msg = f'expected float, got {type(value).__name__}'
            raise ValidationError(msg)
        f = float(value)
        if self._bounds is not None and validate:
            check_bounds(f, self._bounds)
        return f

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> float:
        """JSON number or numeric string → ``float`` (rejects ``bool``); strict mode then checks the bounds."""
        if self._bounds is None:
            kind = type(value)
            if kind is float:
                return value
            if kind is int:
                return float(value)
        if isinstance(value, bool):
            if validate:
                msg = 'expected float, got bool'
                raise ValidationError(msg)
            return float(value)
        if isinstance(value, (int, float)):
            f = float(value)
        elif isinstance(value, str):
            try:
                f = float(value)
            except ValueError as e:
                msg = f'cannot deserialize {value!r} as float'
                raise ValidationError(msg) from e
        else:
            msg = f'cannot deserialize {value!r} as float'
            raise ValidationError(msg)
        if self._bounds is not None and validate:
            check_bounds(f, self._bounds)
        return f
