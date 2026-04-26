"""Pin: CSV codec — class-method-only. Flat dataclasses round-trip;
nested / many / keyed fields raise ``TypeError``."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal as D

import pytest

import seared as s


@s.seared
class Row(s.Seared):
    id: int = s.Int(required=True)
    name: str = s.Str(required=True)
    score: float = s.Float(missing=0.0)


class TestFlatRoundTrip:
    def test_to_csv_includes_header_and_rows(self):
        rows = [
            Row(id=1, name='alice', score=9.5),
            Row(id=2, name='bob',   score=7.2),
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
            tags: list = s.Str(many=True, missing=[])

        with pytest.raises(TypeError, match='keyed/many'):
            Bag.to_csv([Bag(id=1, tags=['x'])])

    def test_keyed_field_rejected(self):
        @s.seared
        class Doc(s.Seared):
            id: int = s.Int(required=True)
            meta: dict = s.Str(keyed=True, missing={})

        with pytest.raises(TypeError, match='keyed/many'):
            Doc.to_csv([Doc(id=1)])

    def test_union_field_rejected(self):
        @s.seared
        class A(s.Seared):
            v: int = s.Int(required=True)

        @s.seared
        class B(s.Seared):
            r: str = s.Str(missing='')

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
