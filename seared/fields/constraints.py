"""Constraints on a field's values (0.4.4): bounds on ``Int`` and ``Float``, lengths on ``Str``.

``ge=``, ``gt=``, ``le=`` and ``lt=`` bound a number: at most one lower bound
(``ge`` or ``gt``) and one upper (``le`` or ``lt``). ``min_length=`` and
``max_length=`` bound a string's length, in code points, as JSON Schema counts
characters. A field checks them after it coerces a value, on a strict ``load``
and a strict ``dump``, element by element under ``many`` and ``keyed``. A lax
class skips them, as it skips a ``Tuple``'s length check.

A field reduces its options to one record when it's declared, and refuses
there and then a declaration that can't hold: an option of the wrong type, two
bounds on one side, a range with no value in it, or a static ``default`` that
fails them. A field with none pays one ``is None`` test per value, past an
exact-type fast path.

The accelerator declines a class with a constrained field: a backend built for
``SPEC_ABI`` 2 ignores options it doesn't know, so it would skip the check
(``seared._core.accel``).
"""

from __future__ import annotations

import math
import operator

# At runtime, not under ``TYPE_CHECKING``: ``Bound`` names it, and each bounded
# field's ``_bounds`` annotation names ``Bound``, which ``typing.get_type_hints``
# evaluates (0.4.3).
from collections.abc import Callable
from typing import Any, NamedTuple

from seared._core.errors import ValidationError

#: The constraint options a field can declare, in the order they're reported.
OPTIONS: tuple[str, ...] = ('ge', 'gt', 'le', 'lt', 'min_length', 'max_length')

#: One bound as a field holds it: the comparison a value must pass, its symbol
#: for the message, and the bound itself.
type Bound = tuple[Callable[[Any, Any], bool], str, int | float]

#: Each bound option's comparison, as its messages and ``seared.doc``'s notes
#: write it.
SYMBOLS: dict[str, str] = {'ge': '>=', 'gt': '>', 'le': '<=', 'lt': '<'}

#: Each side's two options, by name, with their symbols and comparisons.
_LOWER = (('ge', SYMBOLS['ge'], operator.ge), ('gt', SYMBOLS['gt'], operator.gt))
_UPPER = (('le', SYMBOLS['le'], operator.le), ('lt', SYMBOLS['lt'], operator.lt))


def declared_constraints(field: object) -> dict[str, Any]:
    """The constraint options ``field`` sets, by name, in :data:`OPTIONS` order.

    Any field can be asked: one without the options declares none.

    Args:
        field: A field, such as one from ``Cls.__seared_fields__``.

    Returns:
        Each option the field sets, with its value; empty when it sets none.
    """
    return {name: value for name in OPTIONS if (value := getattr(field, name, None)) is not None}


def number_bounds(field: Any, *, integral: bool) -> tuple[Bound, ...] | None:
    """``field``'s bounds, the lower first, or ``None`` when it declares none.

    Args:
        field: An ``Int`` or a ``Float``, or a subclass of one.
        integral: Whether the bounds must be ``int``s (``Int``'s), rather than
            finite numbers (``Float``'s).

    Returns:
        The bounds, each as a :data:`Bound`, or ``None``.

    Raises:
        TypeError: If a bound has the wrong type, a side has two, or the range
            holds no value.
    """
    owner = type(field).__name__
    chosen: list[tuple[str, str, Callable[[Any, Any], bool], Any]] = []
    for side, which in ((_LOWER, 'a lower'), (_UPPER, 'an upper')):
        named = [
            (name, symbol, passes, value)
            for name, symbol, passes in side
            if (value := getattr(field, name)) is not None
        ]
        if len(named) > 1:
            msg = f'{owner}: {named[0][0]}= and {named[1][0]}= both set {which} bound; keep one'
            raise TypeError(msg)
        chosen.extend(named)
    for name, _, _, bound in chosen:
        _check_bound(owner, name, bound, integral=integral)
    if len(chosen) > 1:
        (lo_name, lo_symbol, _, lo), (hi_name, hi_symbol, _, hi) = chosen
        if lo > hi or (lo == hi and (lo_symbol == '>' or hi_symbol == '<')):
            msg = f'{owner}: {lo_name}={lo!r} and {hi_name}={hi!r} leave no value'
            raise TypeError(msg)
    return tuple((passes, symbol, bound) for _, symbol, passes, bound in chosen) or None


def _check_bound(owner: str, name: str, bound: Any, *, integral: bool) -> None:
    """Refuse a bound of the wrong type, or one JSON can't hold.

    A ``bool`` is refused on either field, as the fields refuse it as a value; a
    ``float`` on an ``Int``; and ``NaN`` or an infinity, which no schema can
    write as a JSON number.
    """
    if isinstance(bound, bool) or not isinstance(bound, int if integral else (int, float)):
        wants = 'an int' if integral else 'a number'
        msg = f'{owner}: {name}= takes {wants}, got {bound!r}'
        raise TypeError(msg)
    if isinstance(bound, float) and not math.isfinite(bound):
        msg = f'{owner}: {name}= takes a finite number, got {bound!r}'
        raise TypeError(msg)


def check_bounds(value: Any, bounds: tuple[Bound, ...]) -> None:
    """Raise unless ``value`` passes every bound.

    Each test is ``not passes(value, bound)``. ``NaN`` fails every comparison,
    so it fails every bound, as JSON Schema has it (``NaN`` isn't a JSON
    number). An infinity passes a lower bound and fails an upper one.

    Raises:
        ValidationError: Naming the first bound ``value`` fails:
            ``must be >= 5, got 2``.
    """
    for passes, symbol, bound in bounds:
        if not passes(value, bound):
            msg = f'must be {symbol} {bound!r}, got {value!r}'
            raise ValidationError(msg)


class StrChecks(NamedTuple):
    """What a ``Str`` checks, reduced once when it's declared."""

    min_length: int | None
    max_length: int | None


def string_checks(field: Any) -> StrChecks | None:
    """``field``'s length bounds, or ``None`` when it declares none.

    Args:
        field: A ``Str``, or a subclass of one.

    Returns:
        The lengths as a :class:`StrChecks`, or ``None``.

    Raises:
        TypeError: If a length isn't a non-negative ``int``, or
            ``min_length`` is greater than ``max_length``.
    """
    owner = type(field).__name__
    lo, hi = field.min_length, field.max_length
    for name, value in (('min_length', lo), ('max_length', hi)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            msg = f'{owner}: {name}= takes a non-negative int, got {value!r}'
            raise TypeError(msg)
    if lo is not None and hi is not None and lo > hi:
        msg = f'{owner}: min_length={lo} and max_length={hi} leave no value'
        raise TypeError(msg)
    if lo is None and hi is None:
        return None
    return StrChecks(lo, hi)


def check_string(text: str, checks: StrChecks) -> None:
    """Raise unless ``text`` passes ``checks``.

    A length is ``len(text)``: code points, as JSON Schema counts characters
    (RFC 8259's), so an emoji is one, where JavaScript's ``.length`` says two.

    Raises:
        ValidationError: ``must be at least 3 characters long, got 2``, or
            ``at most``.
    """
    n = len(text)
    if checks.min_length is not None and n < checks.min_length:
        msg = f'must be at least {_characters(checks.min_length)} long, got {n}'
        raise ValidationError(msg)
    if checks.max_length is not None and n > checks.max_length:
        msg = f'must be at most {_characters(checks.max_length)} long, got {n}'
        raise ValidationError(msg)


def _characters(n: int) -> str:
    return '1 character' if n == 1 else f'{n} characters'


def check_default(field: Any, check: Callable[[Any], None]) -> None:
    """Refuse a static ``default`` that fails the field's own ``check``.

    Each element of a ``many`` or ``keyed`` default is checked. An absent key
    takes the default without ``deserialize``, so a bad one would reach the
    object unchecked; JSON Schema also expects a ``default`` to validate
    against its own schema. A ``default_factory`` isn't called to check it.

    Raises:
        TypeError: Naming the default and the check it fails:
            ``Int: default -1 fails its constraints: must be >= 0, got -1``.
    """
    default = field.default
    if field.default_factory is not None or default is None:
        return
    if field.keyed and isinstance(default, dict):
        values = default.values()
    elif field.many and isinstance(default, (list, tuple)):
        values = default
    else:
        values = (default,)
    for value in values:
        try:
            check(value)
        except ValidationError as e:
            msg = f'{type(field).__name__}: default {value!r} fails its constraints: {e.reason}'
            raise TypeError(msg) from None


__all__ = [
    'OPTIONS',
    'SYMBOLS',
    'Bound',
    'StrChecks',
    'check_bounds',
    'check_default',
    'check_string',
    'declared_constraints',
    'number_bounds',
    'string_checks',
]
