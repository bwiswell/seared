"""Pin: CSV codec — class-method-only. Flat dataclasses round-trip;
nested / many / keyed fields raise ``TypeError``."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

import pytest

import seared as s


@s.seared
class Row(s.Seared):
    id: int = s.Int(required=True)
    name: str = s.Str(required=True)
    score: float = s.Float(default=0.0)


class TestFlatRoundTrip:
    def test_to_csv_includes_header_and_rows(self):
        rows = [
            Row(id=1, name='alice', score=9.5),
            Row(id=2, name='bob', score=7.2),
        ]
        text = Row.to_csv(rows)
        lines = text.strip().splitlines()
        assert lines[0] == 'id,name,score'
        assert 'alice' in lines[1]
        assert 'bob' in lines[2]

    def test_from_csv_returns_list(self):
        text = 'id,name,score\n1,alice,9.5\n2,bob,7.2\n'
        rows = Row.from_csv(text)
        assert isinstance(rows, list)
        assert len(rows) == 2
        assert rows[0].name == 'alice'
        # Note: from_csv reads cells as strings; load coerces via field
        # types. Int and Float fields tolerate string inputs.
        assert rows[0].id == 1
        assert rows[0].score == 9.5

    def test_round_trip(self):
        original = [
            Row(id=10, name='x', score=1.0),
            Row(id=11, name='y', score=2.5),
        ]
        loaded = Row.from_csv(Row.to_csv(original))
        assert [r.id for r in loaded] == [10, 11]
        assert [r.name for r in loaded] == ['x', 'y']
        assert [r.score for r in loaded] == [1.0, 2.5]

    def test_from_csv_file(self, tmp_path):
        f = tmp_path / 'rows.csv'
        f.write_text('id,name,score\n5,zelda,8.0\n')
        rows = Row.from_csv(str(f))
        assert rows[0].name == 'zelda'


class TestEmptyInput:
    def test_empty_string_returns_empty_list(self):
        assert Row.from_csv('') == []

    def test_header_only_returns_empty_list(self):
        assert Row.from_csv('id,name,score\n') == []


class TestRejectsNested:
    def test_T_field_rejected(self):
        @s.seared
        class Inner(s.Seared):
            v: int = s.Int(required=True)

        @s.seared
        class Outer(s.Seared):
            id: int = s.Int(required=True)
            nested: Inner = s.T(Inner, required=True)

        with pytest.raises(TypeError, match='flat'):
            Outer.to_csv([Outer(id=1, nested=Inner(v=1))])

    def test_many_field_rejected(self):
        @s.seared
        class Bag(s.Seared):
            id: int = s.Int(required=True)
            tags: list = s.Str(many=True, default=[])

        with pytest.raises(TypeError, match='keyed/many'):
            Bag.to_csv([Bag(id=1, tags=['x'])])

    def test_keyed_field_rejected(self):
        @s.seared
        class Doc(s.Seared):
            id: int = s.Int(required=True)
            meta: dict = s.Str(keyed=True, default={})

        with pytest.raises(TypeError, match='keyed/many'):
            Doc.to_csv([Doc(id=1)])

    def test_union_field_rejected(self):
        @s.seared
        class A(s.Seared):
            v: int = s.Int(required=True)

        @s.seared
        class B(s.Seared):
            r: str = s.Str(default='')

        @s.seared
        class WithUnion(s.Seared):
            id: int = s.Int(required=True)
            action: object = s.Union(variants={'a': A, 'b': B})

        with pytest.raises(TypeError, match='flat'):
            WithUnion.to_csv([WithUnion(id=1, action=A(v=1))])


class TestDateDecimalRoundTrip:
    """Pin: ``Date`` / ``Decimal`` cells round-trip via the existing
    string serialization on ``dump`` / ``load``."""

    def test_date_round_trip(self):
        @s.seared
        class Event(s.Seared):
            id: int = s.Int(required=True)
            when: date = s.Date(required=True)

        rows = [Event(id=1, when=date(2026, 4, 24))]
        loaded = Event.from_csv(Event.to_csv(rows))
        assert loaded[0].when == date(2026, 4, 24)

    def test_decimal_round_trip(self):
        @s.seared
        class Money(s.Seared):
            id: int = s.Int(required=True)
            amount: D = s.Decimal(required=True)

        rows = [Money(id=1, amount=D('1234.56789'))]
        loaded = Money.from_csv(Money.to_csv(rows))
        assert loaded[0].amount == D('1234.56789')


class TestErrorPaths:
    """Pin: a bad record names its 0-based index among the data rows, header not counted."""

    def test_from_csv_names_the_record(self):
        text = 'id,name,score\n1,a,1.0\n2,b,2.0\nthree,c,3.0\n'
        with pytest.raises(s.ValidationError) as info:
            Row.from_csv(text)
        assert info.value.path == (2, 'id')
        assert str(info.value) == "Row[2].id: cannot deserialize 'three' as int"

    def test_to_csv_names_the_record(self):
        rows = [Row(id=1, name='a'), Row(id='x', name='b')]
        with pytest.raises(s.ValidationError) as info:
            Row.to_csv(rows)
        assert info.value.path == (1, 'id')
        assert str(info.value) == 'Row[1].id: expected int, got str'


class TestShortRows:
    """Pin: a short row's missing cells (``None`` from ``DictReader``) are null, as an empty cell is."""

    def test_a_missing_cell_takes_the_default(self):
        (row,) = Row.from_csv('id,name,score\n1,a\n')
        assert row.score == 0.0

    def test_a_missing_required_cell_is_missing(self):
        with pytest.raises(s.ValidationError) as info:
            Row.from_csv('id,name,score\n1\n')
        assert str(info.value) == 'Row[0].name: required key missing'

    def test_a_missing_cell_on_a_nullable_field_is_none(self):
        (row,) = _Nulls.from_csv('id,scale\n1\n')
        assert row.scale is None


@s.seared
class _Wired(s.Seared):
    port: int = s.Int(required=True, data_key='Port')
    host: str = s.Str(default='localhost', data_key='Host')
    secret: str | None = s.Str(default=None, dump=False)


class TestHeader:
    """Pin: each column is headed by the wire key ``dump`` writes, and ``from_csv`` reads it back by."""

    def test_a_data_key_names_its_column(self):
        text = _Wired.to_csv([_Wired(port=7447)])
        assert text.splitlines()[0] == 'Port,Host'
        assert _Wired.from_csv(text) == [_Wired(port=7447)]

    def test_a_dump_false_field_gets_no_column(self):
        # ``dump`` never writes it, so its column could only ever be empty.
        text = _Wired.to_csv([_Wired(port=1, secret='s')])
        assert 'secret' not in text.splitlines()[0]

    def test_a_file_headed_by_wire_keys_loads(self):
        (row,) = _Wired.from_csv('Port,Host\n8080,example\n')
        assert (row.port, row.host) == (8080, 'example')


@s.seared
class _Nulls(s.Seared):
    id: int = s.Int(required=True)
    count: int | None = s.Int()
    ratio: float = s.Float(default=0.5)
    flag: bool | None = s.Bool()
    when: date | None = s.Date()
    amount: D | None = s.Decimal()
    note: str | None = s.Str()
    scale: float | None = s.Float(nullable=True, default=1.0)
    label: str = s.Str(default='none')


class TestEmptyCells:
    """Pin: an empty cell is CSV's null, read through 0.4.0's null rule.

    ``to_csv`` writes every ``None`` as an empty cell, so reading one back as
    null is what lets a ``None`` round-trip. The cost: an empty *string* can't,
    since it shares the one empty value with ``None``.
    """

    def test_an_empty_cell_takes_the_default(self):
        (row,) = _Nulls.from_csv('id,count,ratio,label\n1,,,\n')
        assert (row.count, row.ratio, row.label) == (None, 0.5, 'none')

    def test_an_empty_cell_on_a_nullable_field_is_none(self):
        (row,) = _Nulls.from_csv('id,scale\n1,\n')
        assert row.scale is None

    def test_an_empty_required_cell_is_missing(self):
        with pytest.raises(s.ValidationError) as info:
            _Nulls.from_csv('id,count\n,3\n')
        assert str(info.value) == '_Nulls[0].id: required key missing'

    def test_none_round_trips_for_every_kind(self):
        rows = [
            _Nulls(id=1, scale=None),
            _Nulls(id=2, count=3, ratio=2.5, flag=False, when=date(2026, 1, 2), amount=D('1.25'), note='hi', scale=3.0),
        ]
        assert _Nulls.from_csv(_Nulls.to_csv(rows)) == rows

    def test_an_empty_string_does_not_survive(self):
        (back,) = _Nulls.from_csv(_Nulls.to_csv([_Nulls(id=1, note='', label='')]))
        assert (back.note, back.label) == (None, 'none')


class TestUnknownColumns:
    """An extra column is an unknown key in every row (0.4.1)."""

    def test_by_default_an_extra_column_is_ignored(self):
        assert Row.from_csv('id,name,extra\n1,a,x\n') == [Row(id=1, name='a')]

    def test_a_call_can_refuse_it(self):
        with pytest.raises(s.ValidationError, match='extra: unknown key'):
            Row.from_csv('id,name,extra\n1,a,x\n', unknown='raise')
