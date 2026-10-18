"""Tests for ``seared/fields/__init__.py`` — the field registry. Pins a
property every scalar kind it exports must hold: a value survives a round trip
through the field's *string* form, in strict mode.

zeared depends on it twice over. A topic capture is always a string, and
zeared decodes it with ``Field.deserialize(raw, validate=True)``; a template
slot renders from the field's serialised value. So for every scalar kind,
``f.deserialize(str(f.serialize(v)), validate=True)`` must give ``v`` back, and
a change to strict coercion that broke it would break topic keys quietly.

It also records which kinds are safe as a single topic segment: their string
form never carries the key separator ``/``, nor Zenoh's reserved ``*``, ``$``,
``?`` and ``#``.
"""

from __future__ import annotations

import datetime as dt
import decimal
import enum
import pathlib
import uuid
from typing import Any

import pytest

import seared as s
from seared import fields


class _Zone(enum.Enum):
    NORTH = 'n'


class _Level(enum.Enum):
    LOW = 1
    HIGH = 2


_UTC_MINUS_5 = dt.timezone(dt.timedelta(hours=-5))

# ``(id, field, value)``. Values are chosen to probe each kind's edges, never
# to carry a reserved character themselves: whether a ``Str`` is a safe
# segment is its value's business, not the kind's.
CASES: list[tuple[str, Any, Any]] = [
    ('Bool-true', s.Bool(), True),
    ('Bool-false', s.Bool(), False),
    ('Int-zero', s.Int(), 0),
    ('Int-negative', s.Int(), -42),
    ('Int-beyond-64-bit', s.Int(), 10**20),
    ('Float', s.Float(), 1.5),
    ('Float-tenth', s.Float(), 0.1),
    ('Float-exponent', s.Float(), 1e-07),
    ('Float-negative-zero', s.Float(), -0.0),
    ('Float-inf', s.Float(), float('inf')),
    ('Float-nan', s.Float(), float('nan')),
    ('Str', s.Str(), 'abc'),
    ('Str-space', s.Str(), 'with space'),
    ('Enum-str', s.Enum(enum=_Zone), _Zone.NORTH),
    ('Enum-int', s.Enum(enum=_Level), _Level.HIGH),
    ('Decimal', s.Decimal(), decimal.Decimal('1.10')),
    ('Decimal-exponent', s.Decimal(), decimal.Decimal('1E+2')),
    # ``as_number`` goes through a float, so it is exact only within float
    # precision; the field documents the loss beyond that.
    ('Decimal-as-number', s.Decimal(as_number=True), decimal.Decimal('1.25')),
    ('UUID', s.UUID(), uuid.UUID('9a0a47cd-b6a5-402d-8b45-e79d363690c6')),
    ('Date', s.Date(), dt.date(2026, 10, 16)),
    ('Date-format', s.Date(format='%Y%m%d'), dt.date(2026, 10, 16)),
    ('Time', s.Time(), dt.time(12, 30, 1, 5)),
    ('Time-aware', s.Time(), dt.time(12, 30, tzinfo=dt.UTC)),
    ('Time-format', s.Time(format='%H%M%S'), dt.time(12, 30, 1)),
    ('DateTime-naive', s.DateTime(), dt.datetime(2026, 10, 16, 12, 30, 1, 5)),
    ('DateTime-utc', s.DateTime(), dt.datetime(2026, 10, 16, 12, 30, tzinfo=dt.UTC)),
    ('DateTime-offset', s.DateTime(), dt.datetime(2026, 10, 16, 12, 30, tzinfo=_UTC_MINUS_5)),
    ('DateTime-format', s.DateTime(format='%Y%m%dT%H%M%S'), dt.datetime(2026, 10, 16, 12, 30, 1)),
    ('TimeDelta', s.TimeDelta(), dt.timedelta(seconds=1.5)),
    ('TimeDelta-microsecond', s.TimeDelta(), dt.timedelta(microseconds=1)),
    ('TimeDelta-negative', s.TimeDelta(), dt.timedelta(days=-1, seconds=5)),
    ('Path', s.Path(), pathlib.Path('a/b')),
    ('Bytes-base64', s.Bytes(), b'\xfb\xff\x00'),
    ('Bytes-hex', s.Bytes(encoding='hex'), b'\xfb\xff\x00'),
]
_IDS = [case_id for case_id, _, _ in CASES]

#: Cases whose string form carries a reserved character whatever the value
#: holds: a path's separator, and base64's ``/`` (``b'\xfb\xff\x00'`` encodes
#: to ``'+/8A'``). Hex is the segment-safe way to put bytes in a key.
SEGMENT_UNSAFE = {'Path', 'Bytes-base64'}

_RESERVED = frozenset('/*$?#')

#: Registry names that aren't scalars, so have no single string form.
NON_SCALAR = {'Field', 'T', 'Tuple', 'Union', 'Dict', 'NDArray', 'PandasFrame', 'PolarsFrame'}


def _same(a: Any, b: Any) -> bool:
    """Equal and of one type; floats by ``repr``, so ``nan`` and ``-0.0`` count."""
    if type(a) is not type(b):
        return False
    if isinstance(a, float):
        return repr(a) == repr(b)
    return a == b


@pytest.mark.parametrize(('case_id', 'field', 'value'), CASES, ids=_IDS)
def test_a_value_survives_its_string_form(case_id, field, value):
    text = str(field.serialize(value, validate=True))
    assert _same(field.deserialize(text, validate=True), value), f'{case_id}: {text!r}'


@pytest.mark.parametrize(('case_id', 'field', 'value'), CASES, ids=_IDS)
def test_segment_safety_is_as_recorded(case_id, field, value):
    text = str(field.serialize(value, validate=True))
    assert bool(_RESERVED & set(text)) == (case_id in SEGMENT_UNSAFE), f'{case_id}: {text!r}'


def test_every_scalar_kind_has_a_case():
    # A scalar kind added to the registry without a case here fails, rather
    # than leaving its string form unchecked.
    covered = {type(field).__name__ for _, field, _ in CASES}
    assert not covered & NON_SCALAR
    assert covered | NON_SCALAR == set(fields.__all__)


@pytest.mark.parametrize('name', sorted(fields.__all__))
def test_every_field_classs_annotations_resolve(name):
    # 0.4.3: `typing.get_type_hints` raised `NameError` on every field class,
    # since `default_factory`'s annotation names `Callable`, imported only for
    # type checking (and `Enum`'s and `Union`'s named their own such types).
    import typing

    typing.get_type_hints(getattr(fields, name))
