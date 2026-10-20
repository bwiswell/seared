from __future__ import annotations

import math
import re

import pytest

import seared as s


class TestFloat:
    def test_load_and_dump(self):
        @s.seared
        class Obj(s.Seared):
            val: float = s.Float(required=True)

        obj = Obj.load({'val': 3.14})
        assert abs(obj.val - 3.14) < 1e-9
        assert abs(Obj.dump(obj)['val'] - 3.14) < 1e-9

    def test_many_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            vals: list = s.Float(many=True, required=True)

        obj = Obj.load({'vals': [1.1, 2.2, 3.3]})
        assert len(obj.vals) == 3
        d = Obj.dump(obj)
        assert len(d['vals']) == 3

    def test_keyed_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            rates: dict = s.Float(keyed=True, required=True)

        obj = Obj.load({'rates': {'a': 0.5, 'b': 1.5}})
        assert abs(obj.rates['a'] - 0.5) < 1e-9
        d = Obj.dump(obj)
        assert abs(d['rates']['a'] - 0.5) < 1e-9


class TestNumbers:
    """Pin: an exact ``int`` or ``float`` takes a fast path (0.4.4) that answers as the full one did."""

    @pytest.mark.parametrize('method', ['deserialize', 'serialize'])
    def test_an_int_becomes_a_float(self, method):
        out = getattr(s.Float(), method)(7)
        assert out == 7.0
        assert type(out) is float

    @pytest.mark.parametrize('method', ['deserialize', 'serialize'])
    def test_a_bool_is_refused_strict(self, method):
        with pytest.raises(s.ValidationError, match=r'^expected float, got bool$'):
            getattr(s.Float(), method)(value=True)

    def test_a_bool_is_read_lax(self):
        assert s.Float().deserialize(value=True, validate=False) == 1.0


@s.seared
class Ratio(s.Seared):
    r: float = s.Float(ge=0, le=1, default=0.0)


@s.seared(validate=False)
class LaxRatio(s.Seared):
    r: float = s.Float(ge=0, le=1, default=0.0)


class TestBounds:
    """Pin: bounds on a float, ``NaN`` and the infinities included (0.4.4)."""

    @pytest.mark.parametrize(
        ('options', 'inside', 'outside', 'reason'),
        [
            ({'ge': 0.5}, 0.5, 0.25, 'must be >= 0.5, got 0.25'),
            ({'gt': 0}, 0.001, 0.0, 'must be > 0, got 0.0'),
            ({'le': 1.5}, 1.5, 1.75, 'must be <= 1.5, got 1.75'),
            ({'lt': 1}, 0.999, 1.0, 'must be < 1, got 1.0'),
        ],
    )
    def test_each_option(self, options, inside, outside, reason):
        field = s.Float(**options)
        assert field.deserialize(inside) == inside
        assert field.serialize(inside) == inside
        with pytest.raises(s.ValidationError, match=f'^{re.escape(reason)}$'):
            field.deserialize(outside)
        with pytest.raises(s.ValidationError, match=f'^{re.escape(reason)}$'):
            field.serialize(outside)

    def test_an_int_is_checked_as_a_float(self):
        with pytest.raises(s.ValidationError, match=r'^must be <= 1, got 2\.0$'):
            s.Float(le=1).deserialize(2)

    def test_a_numeric_string_is_checked(self):
        with pytest.raises(s.ValidationError, match=r'^Ratio\.r: must be <= 1, got 1\.5$'):
            Ratio.load({'r': '1.5'})

    @pytest.mark.parametrize('raw', [math.nan, 'nan'])
    def test_a_bounded_field_refuses_nan(self, raw):
        with pytest.raises(s.ValidationError, match=r'^Ratio\.r: must be >= 0, got nan$'):
            Ratio.load({'r': raw})

    def test_an_unbounded_field_still_takes_nan(self):
        assert math.isnan(s.Float().deserialize(math.nan))

    def test_an_infinity_passes_a_lower_bound_and_fails_an_upper_one(self):
        assert s.Float(ge=0).deserialize('inf') == math.inf
        with pytest.raises(s.ValidationError, match=r'^must be <= 1, got inf$'):
            s.Float(le=1).deserialize('inf')

    def test_a_dump_refuses_a_constructed_value_outside_them(self):
        with pytest.raises(s.ValidationError, match=r'^Ratio\.r: must be <= 1, got 1\.5$'):
            Ratio.dump(Ratio(r=1.5))

    def test_lax_mode_skips_them(self):
        assert LaxRatio.load({'r': 2.0}).r == 2.0
        assert LaxRatio.dump(LaxRatio(r=-1.0)) == {'r': -1.0}
