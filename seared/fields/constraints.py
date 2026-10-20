r"""Constraints on a field's values (0.4.4): bounds on ``Int`` and ``Float``; lengths and a pattern on ``Str``.

``ge=``, ``gt=``, ``le=`` and ``lt=`` bound a number: at most one lower bound
(``ge`` or ``gt``) and one upper (``le`` or ``lt``). ``min_length=`` and
``max_length=`` bound a string's length, in code points, as JSON Schema counts
characters, and ``pattern=`` is a regex the string must contain a match for. A
field checks them after it coerces a value, on a strict ``load`` and a strict
``dump``, element by element under ``many`` and ``keyed``. A lax class skips
them, as it skips a ``Tuple``'s length check.

A pattern is JSON Schema's: an ECMA-262 regex, searched for rather than
anchored. Python's ``re`` reads some regexes differently (``$`` before a final
newline, ``.`` on ``\r``, ``\d`` on any digit), and refuses or warns on some
that ECMA-262 takes, so a pattern must stay within the subset both read the
same way, and is compiled from a translation of it (:func:`portable_regex`).

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
import re
import string
import warnings

# At runtime, not under ``TYPE_CHECKING``: ``Bound`` names it, and each bounded
# field's ``_bounds`` annotation names ``Bound``, which ``typing.get_type_hints``
# evaluates (0.4.3).
from collections.abc import Callable
from typing import Any, NamedTuple

from seared._core.errors import ValidationError

#: The constraint options a field can declare, in the order they're reported.
OPTIONS: tuple[str, ...] = ('ge', 'gt', 'le', 'lt', 'min_length', 'max_length', 'pattern')

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
    #: The pattern as declared, which the schema and the messages show.
    pattern: str | None = None
    #: Its translation, compiled: what the check searches with.
    regex: re.Pattern[str] | None = None


def string_checks(field: Any) -> StrChecks | None:
    """``field``'s lengths and pattern, or ``None`` when it declares neither.

    Args:
        field: A ``Str``, or a subclass of one.

    Returns:
        The checks as a :class:`StrChecks`, or ``None``.

    Raises:
        TypeError: If a length isn't a non-negative ``int``, ``min_length`` is
            greater than ``max_length``, or the pattern isn't a ``str`` within
            the portable subset (:func:`portable_regex`).
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
    pattern = field.pattern
    if lo is None and hi is None and pattern is None:
        return None
    regex = None if pattern is None else portable_regex(pattern, owner)
    return StrChecks(lo, hi, pattern, regex)


def check_string(text: str, checks: StrChecks) -> None:
    """Raise unless ``text`` passes ``checks``.

    A length is ``len(text)``: code points, as JSON Schema counts characters
    (RFC 8259's), so an emoji is one, where JavaScript's ``.length`` says two.
    A pattern's message names the pattern and never the value: a pattern most
    often guards the shape of a name, and the value that fails one is the
    likeliest to be a secret pasted in its place.

    Raises:
        ValidationError: ``must be at least 3 characters long, got 2``, ``at
            most``, or ``must match the pattern '^[a-z]+$'``.
    """
    n = len(text)
    if checks.min_length is not None and n < checks.min_length:
        msg = f'must be at least {_characters(checks.min_length)} long, got {n}'
        raise ValidationError(msg)
    if checks.max_length is not None and n > checks.max_length:
        msg = f'must be at most {_characters(checks.max_length)} long, got {n}'
        raise ValidationError(msg)
    if checks.regex is not None and checks.regex.search(text) is None:
        msg = f'must match the pattern {checks.pattern!r}'
        raise ValidationError(msg)


def _characters(n: int) -> str:
    return '1 character' if n == 1 else f'{n} characters'


# --- Patterns: the portable subset ----------------------------------------------------------
#
# The allow-list (docs/fields/constraints.md says it for users):
#
# - characters: literals; escapes of the syntax characters ``^ $ \ . * + ? ( ) [ ] { } | /``
#   (and ``-`` inside a class); ``\n \r \t \f \v``; ``\xHH``; ``\uHHHH`` outside the surrogates;
# - ``^``, ``$`` and ``.``;
# - groups ``(...)`` and ``(?:...)``, lookaheads ``(?=...)`` and ``(?!...)``, and ``|``;
# - classes ``[...]`` and ``[^...]`` with ranges, where ``]`` can't come first, ``[`` and a
#   doubled ``&&``, ``||`` or ``~~`` can't appear, and a bare ``-`` only starts or ends one;
# - quantifiers ``*``, ``+``, ``?``, ``{n}``, ``{n,}`` and ``{n,m}``, each optionally lazy, after
#   something they can repeat (never an assertion: ``^``, ``$``, a lookahead).
#
# Each refusal is a difference found by running both engines: ECMA-262 (with the ``u`` flag, as
# JSON Schema validators compile it) raises ``SyntaxError`` on it, Python raises or warns, or the
# two compile it and match differently.

#: What ``.`` matches in ECMA-262: any character but a line terminator. Python's
#: ``.`` stops only at ``\n``.
_DOT = r'[^\n\r\u2028\u2029]'

#: The characters an escape may name outside a class: ECMA-262's syntax
#: characters and ``/``. Inside a class, ``-`` too.
_SYNTAX = frozenset('^$\\.*+?()[]{}|/')

#: The control escapes both engines read the same way.
_CONTROLS = frozenset('nrtfv')

#: An escape outside the subset, with its portable spelling.
_ESCAPE_FIXES = {
    'd': 'write [0-9]',
    'D': 'write [^0-9]',
    'w': 'write [A-Za-z0-9_]',
    'W': 'write [^A-Za-z0-9_]',
    's': r'write the whitespace you mean as a class, such as [ \t\n\r]',
    'S': r'write the whitespace you mean as a negated class, such as [^ \t\n\r]',
    'A': 'write ^',
    'Z': 'write $',
    'z': 'write $',
    'c': r'write \xHH',
    'p': 'write the characters as a class',
    'P': 'write the characters as a negated class',
}

#: An escape outside the subset with no portable spelling, by what it is.
_ESCAPE_NAMES = {'b': 'a word boundary', 'B': 'a word boundary', 'k': 'a named backreference'}

#: Each ``(?`` opening outside the subset, by what it is.
_GROUP_NAMES = (
    ('(?<=', 'lookbehind'),
    ('(?<!', 'lookbehind'),
    ('(?P', 'a named group'),
    ('(?<', 'a named group'),
    ('(?>', 'an atomic group'),
    ('(?#', 'a comment'),
    ('(?(', 'a conditional'),
)

_REPEAT = re.compile(r'\{(\d+)(,(\d*))?\}')
_REPEAT_FROM_NONE = re.compile(r'\{,(\d+)\}')


class _UnportableError(Exception):
    """A construct outside the portable subset; its message says what, where, and the fix."""


def _unportable(at: int, construct: str, *, fix: str | None = None, name: str | None = None) -> _UnportableError:
    text = f"{construct} at {at} isn't portable"
    if name is not None:
        text += f' ({name})'
    if fix is not None:
        text += f'; {fix}'
    return _UnportableError(text)


def portable_regex(pattern: Any, owner: str = 'Str') -> re.Pattern[str]:
    r"""``pattern`` compiled to match as JSON Schema's ECMA-262 regexes do.

    ``pattern`` must stay within the subset both engines read the same way
    (the comment above lists it). Outside a class, ``$`` becomes ``\Z`` and
    ``.`` becomes ``[^\n\r\u2028\u2029]``; everything else in the subset means
    the same in both and is kept as written. The check is ``search``: a
    pattern is unanchored, as JSON Schema's is, and ``^...$`` anchors it.

    Args:
        pattern: The pattern as declared.
        owner: The field class's name, for the message.

    Returns:
        The translation, compiled.

    Raises:
        TypeError: If ``pattern`` isn't a ``str``, has a construct outside the
            subset (the message names it, where it is, and its portable
            spelling where there's one), or doesn't compile.
    """
    if not isinstance(pattern, str):
        compiled = isinstance(pattern, re.Pattern)
        got = 'a compiled pattern, whose flags JSON Schema has no form for' if compiled else repr(pattern)
        msg = f'{owner}: pattern= takes a str, got {got}'
        raise TypeError(msg)
    try:
        translated = _translate(pattern)
    except _UnportableError as e:
        msg = f'{owner}: pattern={pattern!r}: {e}'
        raise TypeError(msg) from None
    try:
        # A warning is Python reading the pattern another way (a possible set
        # operation, say), so it refuses the pattern as an error does. A count
        # past ``re``'s limit (``a{99999999999}``) raises ``OverflowError``.
        with warnings.catch_warnings(action='error'):
            return re.compile(translated)
    except (re.error, OverflowError, Warning) as e:
        msg = f"{owner}: pattern={pattern!r} doesn't compile: {e}"
        raise TypeError(msg) from None


def _translate(pattern: str) -> str:  # noqa: C901, PLR0912, PLR0915 — one flat scan: a branch per construct
    """``pattern`` as Python reads it the way ECMA-262 does, refusing anything outside the subset."""
    out: list[str] = []
    opened: list[tuple[int, bool]] = []  # each open group: where it opened, and whether it's a lookahead
    # What a quantifier here would repeat: something (True), an assertion (False), or nothing (None).
    repeatable: bool | None = None
    i, n = 0, len(pattern)
    while i < n:
        c = pattern[i]
        if _is_surrogate(c):
            raise _unportable(i, repr(c), fix='write the character itself, not its surrogates')
        if c == '\\':
            text, i = _escape(pattern, i, in_class=False)
            out.append(text)
            repeatable = True
        elif c == '[':
            text, i = _class(pattern, i)
            out.append(text)
            repeatable = True
        elif c == '(':
            lookahead, width = _group(pattern, i)
            opened.append((i, lookahead))
            out.append(pattern[i : i + width])
            i += width
            repeatable = None
        elif c == ')':
            if not opened:
                msg = f') at {i} closes no group'
                raise _UnportableError(msg)
            _, lookahead = opened.pop()
            out.append(')')
            i += 1
            repeatable = not lookahead
        elif c in '*+?{':
            end = _quantifier(pattern, i, repeatable)
            out.append(pattern[i:end])
            i = end
            repeatable = None
        elif c in ']}':
            raise _unportable(i, c, fix=f'escape it as \\{c}')
        else:
            if c == '$':
                out.append(r'\Z')
                repeatable = False
            elif c == '^':
                out.append(c)
                repeatable = False
            elif c == '|':
                out.append(c)
                repeatable = None
            else:
                out.append(_DOT if c == '.' else c)
                repeatable = True
            i += 1
    if opened:
        msg = f'( at {opened[-1][0]} is never closed'
        raise _UnportableError(msg)
    return ''.join(out)


def _is_surrogate(c: str) -> bool:
    # ECMA-262 joins a high and a low surrogate into one character; Python keeps two.
    return '\ud800' <= c <= '\udfff'


def _escape(pattern: str, i: int, *, in_class: bool) -> tuple[str, int]:  # noqa: C901 — a branch per escape
    """The escape at ``i``, kept as written, and where it ends; refusing one outside the subset."""
    if i + 1 >= len(pattern):
        msg = f'\\ at {i} escapes nothing'
        raise _UnportableError(msg)
    e = pattern[i + 1]
    if e in _SYNTAX or e in _CONTROLS or (in_class and e == '-'):
        return pattern[i : i + 2], i + 2
    if e == 'x' and _hex(pattern, i + 2, 2):
        return pattern[i : i + 4], i + 4
    if e == 'u' and _hex(pattern, i + 2, 4):
        if _is_surrogate(chr(int(pattern[i + 2 : i + 6], 16))):
            raise _unportable(i, pattern[i : i + 6], fix='write the character itself, not its surrogates')
        return pattern[i : i + 6], i + 6
    construct = f'\\{e}'
    if e == 'u':
        raise _unportable(i, construct, fix=r'write \uHHHH (four hex digits), or the character itself')
    if e == '-':
        raise _unportable(i, construct, fix='write a plain -, which needs no escape outside a class')
    if e == '0':
        raise _unportable(i, construct, fix=r'write \x00')
    if e.isdigit():
        raise _unportable(i, construct, name='a backreference')
    if e == 'b' and in_class:
        raise _unportable(i, construct, fix=r'write \x08')
    if e in _ESCAPE_NAMES:
        raise _unportable(i, construct, name=_ESCAPE_NAMES[e])
    syntax = '^ $ \\ . * + ? ( ) [ ] { } | /' + (' -' if in_class else '')
    raise _unportable(i, construct, fix=_ESCAPE_FIXES.get(e, f'escape only {syntax}'))


def _hex(pattern: str, start: int, count: int) -> bool:
    digits = pattern[start : start + count]
    return len(digits) == count and all(d in string.hexdigits for d in digits)


def _class(pattern: str, i: int) -> tuple[str, int]:
    """The class opening at ``i``, kept as written, and where it ends; refusing what the engines read differently."""
    n = len(pattern)
    j = i + 1
    if j < n and pattern[j] == '^':
        j += 1
    first = j
    if j < n and pattern[j] == ']':
        raise _unportable(j, ']', fix=r"a class can't open with it, so escape it as \]")
    out = [pattern[i:j]]
    while True:
        if j >= n:
            msg = f'[ at {i} is never closed'
            raise _UnportableError(msg)
        if pattern[j] == ']':
            out.append(']')
            return ''.join(out), j + 1
        start = j
        low, j = _class_atom(pattern, j, first)
        if pattern.startswith('-', j) and j + 1 < n and pattern[j + 1] != ']':
            high, end = _class_atom(pattern, j + 1, first)
            if '-' in (low, high):
                at = start if low == '-' else j + 1
                raise _unportable(at, '-', fix=r'escape a range that starts or ends at - as \-')
            out.append(f'{low}-{high}')
            j = end
        else:
            out.append(low)


def _class_atom(pattern: str, j: int, first: int) -> tuple[str, int]:
    """One character of a class, as written, and where it ends."""
    c = pattern[j]
    if _is_surrogate(c):
        raise _unportable(j, repr(c), fix='write the character itself, not its surrogates')
    if c == '\\':
        return _escape(pattern, j, in_class=True)
    if c == '[':
        raise _unportable(j, '[', fix=r'escape it as \[ inside a class')
    if c in '&|~' and pattern.startswith(c * 2, j):
        raise _unportable(j, c * 2, fix=f'escape one of them: \\{c}{c}')
    if c == '-' and j != first and not pattern.startswith(']', j + 1):
        raise _unportable(j, '-', fix=r'escape it as \-, or put it first or last in the class')
    return c, j + 1


def _group(pattern: str, i: int) -> tuple[bool, int]:
    """Whether the group opening at ``i`` is a lookahead, and how long its opening is."""
    if not pattern.startswith('(?', i):
        return False, 1
    head = pattern[i : i + 3]
    if head == '(?:':
        return False, 3
    if head in ('(?=', '(?!'):
        return True, 3
    for prefix, name in _GROUP_NAMES:
        if pattern.startswith(prefix, i):
            raise _unportable(i, prefix, name=name)
    raise _unportable(i, head, name='an inline flag')


def _quantifier(pattern: str, i: int, repeatable: bool | None) -> int:
    """Where the quantifier at ``i`` ends, a lazy ``?`` included; refusing one that repeats nothing or an assertion."""
    if pattern[i] == '{':
        m = _REPEAT.match(pattern, i)
        if m is None:
            if (m := _REPEAT_FROM_NONE.match(pattern, i)) is not None:
                raise _unportable(i, m.group(), fix=f'write {{0,{m.group(1)}}}')
            raise _unportable(i, '{', fix=r'escape it as \{')
        if m.group(3) and int(m.group(3)) < int(m.group(1)):
            msg = f'{m.group()} at {i} counts down; put the smaller number first'
            raise _UnportableError(msg)
        end = m.end()
    else:
        end = i + 1
    if repeatable is None:
        msg = f'{pattern[i:end]} at {i} has nothing to repeat'
        raise _UnportableError(msg)
    if repeatable is False:
        raise _unportable(i, pattern[i:end], name='a repeated assertion')
    if pattern.startswith('?', end):
        end += 1
    if end < len(pattern) and pattern[end] in '*+?{':
        raise _unportable(end, pattern[end], name='a quantifier on a quantifier')
    return end


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
    'portable_regex',
    'string_checks',
]
