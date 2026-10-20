from __future__ import annotations

import dataclasses
import enum
import math
import re

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

    def test_bool_is_refused_by_a_strict_serialize(self):
        with pytest.raises(s.ValidationError, match=r'^expected int, got bool$'):
            s.Int().serialize(value=True)

    @pytest.mark.parametrize('method', ['deserialize', 'serialize'])
    def test_an_int_subclass_takes_the_full_path(self, method):
        # The exact-``int`` fast path (0.4.4) leaves a subclass to the full
        # one: a serialize converts it to a plain ``int``.
        class Level(enum.IntEnum):
            HIGH = 3

        out = getattr(s.Int(), method)(Level.HIGH)
        assert out == 3
        if method == 'serialize':
            assert type(out) is int


@s.seared
class Bounded(s.Seared):
    n: int = s.Int(ge=0, lt=10, default=0)
    ns: list[int] = s.Int(gt=0, many=True, default_factory=list)
    by_name: dict[str, int] = s.Int(le=5, keyed=True, default_factory=dict)


@s.seared(validate=False)
class LaxBounded(s.Seared):
    n: int = s.Int(ge=0, default=0)


class TestBounds:
    """Pin: bounds are checked after coercion, on a strict load and a strict dump (0.4.4)."""

    @pytest.mark.parametrize(
        ('options', 'inside', 'outside', 'reason'),
        [
            ({'ge': 0}, 0, -1, 'must be >= 0, got -1'),
            ({'gt': 0}, 1, 0, 'must be > 0, got 0'),
            ({'le': 9}, 9, 10, 'must be <= 9, got 10'),
            ({'lt': 9}, 8, 9, 'must be < 9, got 9'),
        ],
    )
    def test_each_option(self, options, inside, outside, reason):
        field = s.Int(**options)
        assert field.deserialize(inside) == inside
        assert field.serialize(inside) == inside
        with pytest.raises(s.ValidationError, match=f'^{re.escape(reason)}$'):
            field.deserialize(outside)
        with pytest.raises(s.ValidationError, match=f'^{re.escape(reason)}$'):
            field.serialize(outside)

    @pytest.mark.parametrize('raw', ['-3', -3.0])
    def test_a_coerced_value_is_checked(self, raw):
        with pytest.raises(s.ValidationError, match=r'^must be >= 0, got -3$'):
            s.Int(ge=0).deserialize(raw)

    def test_a_load_names_the_field(self):
        with pytest.raises(s.ValidationError) as info:
            Bounded.load({'n': 10})
        assert str(info.value) == 'Bounded.n: must be < 10, got 10'
        assert info.value.reason == 'must be < 10, got 10'

    def test_a_dump_refuses_a_constructed_value_outside_them(self):
        # Construction checks nothing, as it checks no types; the dump does.
        with pytest.raises(s.ValidationError, match=r'^Bounded\.n: must be >= 0, got -1$'):
            Bounded.dump(Bounded(n=-1))

    def test_a_many_element_is_named_by_its_index(self):
        with pytest.raises(s.ValidationError, match=r'^Bounded\.ns\[1\]: must be > 0, got 0$'):
            Bounded.load({'ns': [1, 0]})

    def test_a_keyed_value_is_named_by_its_key(self):
        with pytest.raises(s.ValidationError, match=r"^Bounded\.by_name\['r-1'\]: must be <= 5, got 6$"):
            Bounded.load({'by_name': {'r-0': 1, 'r-1': 6}})

    def test_lax_mode_skips_them(self):
        assert LaxBounded.load({'n': -1}).n == -1
        assert LaxBounded.dump(LaxBounded(n=-1)) == {'n': -1}
        assert s.Int(ge=0).deserialize(-1, validate=False) == -1

    def test_a_big_int_is_compared_exactly(self):
        field = s.Int(le=10**20)
        assert field.deserialize(10**20) == 10**20
        with pytest.raises(s.ValidationError, match=r'^must be <= 100000000000000000000, got 100000000000000000001$'):
            field.deserialize(10**20 + 1)

    def test_the_reduced_bounds_stay_out_of_equality_and_repr(self):
        assert s.Int(ge=0) == s.Int(ge=0)
        assert s.Int(ge=0) != s.Int(ge=1)
        assert '_bounds' not in repr(s.Int(ge=0))

    def test_replace_reduces_them_again(self):
        field = dataclasses.replace(s.Int(ge=0), ge=5)
        with pytest.raises(s.ValidationError, match=r'^must be >= 5, got 4$'):
            field.deserialize(4)
