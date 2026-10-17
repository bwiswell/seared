from __future__ import annotations

import math

import pytest

import seared as s


class TestInt:
    def test_load_and_dump(self):
        @s.seared
        class Obj(s.Seared):
            val: int = s.Int(required=True)

        obj = Obj.load({'val': 42})
        assert obj.val == 42
        assert Obj.dump(obj) == {'val': 42}

    def test_default(self):
        @s.seared
        class Obj(s.Seared):
            val: int = s.Int(default=0)

        obj = Obj.load({})
        assert obj.val == 0

    def test_many_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            nums: list = s.Int(many=True, required=True)

        obj = Obj.load({'nums': [1, 2, 3]})
        assert obj.nums == [1, 2, 3]
        assert Obj.dump(obj) == {'nums': [1, 2, 3]}

    def test_keyed_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            scores: dict = s.Int(keyed=True, required=True)

        obj = Obj.load({'scores': {'a': 10, 'b': 20}})
        assert obj.scores == {'a': 10, 'b': 20}
        assert Obj.dump(obj) == {'scores': {'a': 10, 'b': 20}}


class TestCoercion:
    """Pin: strict ``Int`` never loses data; lax truncates. Neither lets an ``OverflowError`` out."""

    @pytest.mark.parametrize('validate', [True, False], ids=['strict', 'lax'])
    @pytest.mark.parametrize(('raw', 'want'), [(3.0, 3), (-2.0, -2), ('42', 42), (' 7 ', 7), (10**20, 10**20)])
    def test_lossless_values_load_in_both_modes(self, validate, raw, want):
        assert s.Int().deserialize(raw, validate=validate) == want

    def test_strict_refuses_a_fractional_float(self):
        with pytest.raises(s.ValidationError, match=r'^cannot deserialize 3\.7 as int$'):
            s.Int().deserialize(3.7)

    def test_lax_truncates_a_fractional_float(self):
        assert s.Int().deserialize(3.7, validate=False) == 3

    @pytest.mark.parametrize('validate', [True, False], ids=['strict', 'lax'])
    @pytest.mark.parametrize('raw', [math.inf, -math.inf, math.nan, '3.0', 'x', [1]])
    def test_refused_in_both_modes(self, validate, raw):
        with pytest.raises(s.ValidationError, match=r'as int$'):
            s.Int().deserialize(raw, validate=validate)

    def test_inf_is_a_validation_error_through_load(self):
        @s.seared(validate=False)
        class Obj(s.Seared):
            val: int = s.Int(required=True)

        with pytest.raises(s.ValidationError) as info:
            Obj.load({'val': math.inf})
        assert str(info.value) == 'Obj.val: cannot deserialize inf as int'

    def test_bool_is_refused_strict_and_read_lax(self):
        with pytest.raises(s.ValidationError, match='expected int, got bool'):
            s.Int().deserialize(value=True)
        assert s.Int().deserialize(value=True, validate=False) == 1
