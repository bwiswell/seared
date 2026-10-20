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
class Int(Field):
    KIND = FieldKind.INT

    # Bounds (0.4.4): at most one lower and one upper, each an ``int``, checked
    # on a strict load and dump (``seared.fields.constraints``).
    ge: int | None = None
    gt: int | None = None
    le: int | None = None
    lt: int | None = None
    # The bounds, reduced once at declaration, or ``None``.
    _bounds: tuple[Bound, ...] | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Reduce the bounds to one check, refusing a declaration they can't hold."""
        super().__post_init__()
        bounds = number_bounds(self, integral=True)
        object.__setattr__(self, '_bounds', bounds)
        if bounds is not None:
            check_default(self, lambda value: check_bounds(value, bounds))

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> int:
        """Python ``int`` → JSON integer (rejects ``bool``), within its bounds."""
        # The common case first, and without the slower checks: an exact ``int``
        # on an unbounded field is its own wire form.
        if type(value) is int and self._bounds is None:
            return value
        if validate and (isinstance(value, bool) or not isinstance(value, int)):
            msg = f'expected int, got {type(value).__name__}'
            raise ValidationError(msg)
        n = int(value)
        if self._bounds is not None and validate:
            check_bounds(n, self._bounds)
        return n

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> int:
        """JSON integer, integral float, or numeric string → ``int`` (rejects ``bool``).

        Lax mode also truncates a fractional float (``3.7`` → ``3``) and
        takes ``bool``; neither mode lets an ``OverflowError`` (``inf``) out.
        Strict mode then checks the bounds.
        """
        if type(value) is int and self._bounds is None:
            return value
        if isinstance(value, bool):
            if validate:
                msg = 'expected int, got bool'
                raise ValidationError(msg)
            return int(value)
        if isinstance(value, int):
            n = value
        else:
            coerced = coerce_int(value, validate)
            if coerced is None:
                msg = f'cannot deserialize {value!r} as int'
                raise ValidationError(msg)
            n = coerced
        if self._bounds is not None and validate:
            check_bounds(n, self._bounds)
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
