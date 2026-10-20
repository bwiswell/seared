"""Tests for ``seared.fields.constraints``: what a field declares, and the declarations it refuses (0.4.4)."""

from __future__ import annotations

import math
import re

import pytest

import seared as s
from seared.fields.constraints import check_bounds, declared_constraints, number_bounds


class TestDeclaredConstraints:
    def test_none_on_an_unbounded_field(self):
        assert declared_constraints(s.Int()) == {}

    def test_the_options_set_in_a_fixed_order(self):
        assert declared_constraints(s.Float(lt=1.0, ge=0)) == {'ge': 0, 'lt': 1.0}

    @pytest.mark.parametrize('field', [s.Str(), s.Bool(), s.T(s.Seared), object()])
    def test_none_on_anything_without_the_options(self, field):
        assert declared_constraints(field) == {}


class TestNumberBounds:
    def test_none_when_none_are_declared(self):
        assert number_bounds(s.Int(), integral=True) is None

    def test_the_lower_bound_first(self):
        bounds = number_bounds(s.Int(le=9, gt=0), integral=True)
        assert [(symbol, bound) for _, symbol, bound in bounds] == [('>', 0), ('<=', 9)]

    @pytest.mark.parametrize(('low', 'high'), [('ge', 'le'), ('ge', 'lt'), ('gt', 'le'), ('gt', 'lt')])
    def test_a_range_with_room_is_accepted(self, low, high):
        s.Int(**{low: 1, high: 3})

    def test_a_range_of_one_value_is_accepted(self):
        s.Int(ge=1, le=1)


class TestRefusedDeclarations:
    """Each raises ``TypeError`` where the field is declared."""

    @pytest.mark.parametrize(
        ('field', 'options', 'message'),
        [
            (s.Int, {'ge': 0.5}, 'Int: ge= takes an int, got 0.5'),
            (s.Int, {'lt': True}, 'Int: lt= takes an int, got True'),
            (s.Int, {'le': '9'}, "Int: le= takes an int, got '9'"),
            (s.Float, {'gt': False}, 'Float: gt= takes a number, got False'),
            (s.Float, {'ge': '0'}, "Float: ge= takes a number, got '0'"),
            (s.Float, {'ge': math.nan}, 'Float: ge= takes a finite number, got nan'),
            (s.Float, {'le': math.inf}, 'Float: le= takes a finite number, got inf'),
        ],
    )
    def test_a_bound_of_the_wrong_type(self, field, options, message):
        with pytest.raises(TypeError, match=f'^{re.escape(message)}$'):
            field(**options)

    @pytest.mark.parametrize(
        ('options', 'message'),
        [
            ({'ge': 0, 'gt': 0}, 'Int: ge= and gt= both set a lower bound; keep one'),
            ({'le': 9, 'lt': 9}, 'Int: le= and lt= both set an upper bound; keep one'),
        ],
    )
    def test_two_bounds_on_one_side(self, options, message):
        with pytest.raises(TypeError, match=f'^{re.escape(message)}$'):
            s.Int(**options)

    @pytest.mark.parametrize(
        ('options', 'message'),
        [
            ({'ge': 5, 'le': 1}, 'Int: ge=5 and le=1 leave no value'),
            ({'ge': 1, 'lt': 1}, 'Int: ge=1 and lt=1 leave no value'),
            ({'gt': 1, 'le': 1}, 'Int: gt=1 and le=1 leave no value'),
        ],
    )
    def test_an_empty_range(self, options, message):
        with pytest.raises(TypeError, match=f'^{re.escape(message)}$'):
            s.Int(**options)

    def test_a_float_range_with_an_int_bound(self):
        with pytest.raises(TypeError, match=r'^Float: gt=1 and lt=0\.5 leave no value$'):
            s.Float(gt=1, lt=0.5)


class TestDefaults:
    """A static ``default`` must pass the field's own bounds."""

    def test_a_default_outside_the_bounds_is_refused(self):
        with pytest.raises(TypeError, match=r'^Int: default -1 fails its constraints: must be >= 0, got -1$'):
            s.Int(ge=0, default=-1)

    def test_each_element_of_a_many_default_is_checked(self):
        with pytest.raises(TypeError, match=r'^Float: default 2\.0 fails its constraints: must be < 1\.0, got 2\.0$'):
            s.Float(lt=1.0, many=True, default=[0.5, 2.0])

    def test_each_value_of_a_keyed_default_is_checked(self):
        with pytest.raises(TypeError, match=r'^Int: default 11 fails its constraints'):
            s.Int(le=10, keyed=True, default={'a': 1, 'b': 11})

    def test_a_default_inside_the_bounds_is_accepted(self):
        assert s.Int(ge=0, default=0).default == 0

    def test_a_default_factory_is_not_called(self):
        calls = []
        s.Int(ge=0, default_factory=lambda: calls.append(1))
        assert calls == []


class TestCheckBounds:
    BOUNDS = number_bounds(s.Float(ge=0, le=1), integral=False)

    @pytest.mark.parametrize('value', [0, 0.5, 1])
    def test_a_value_within_passes(self, value):
        check_bounds(value, self.BOUNDS)

    def test_nan_fails_every_bound(self):
        with pytest.raises(s.ValidationError, match=r'^must be >= 0, got nan$'):
            check_bounds(math.nan, self.BOUNDS)
        with pytest.raises(s.ValidationError, match=r'^must be <= 1, got nan$'):
            check_bounds(math.nan, number_bounds(s.Float(le=1), integral=False))

    def test_an_infinity_passes_a_lower_bound_and_fails_an_upper_one(self):
        check_bounds(math.inf, number_bounds(s.Float(ge=0), integral=False))
        with pytest.raises(s.ValidationError, match=r'^must be <= 1, got inf$'):
            check_bounds(math.inf, self.BOUNDS)
