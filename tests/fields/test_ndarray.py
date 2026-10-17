from __future__ import annotations

import numpy as np
import pytest

import seared as s


class TestNDArray:
    def test_load(self):
        @s.seared
        class Obj(s.Seared):
            arr: np.ndarray = s.NDArray(required=True)

        obj = Obj.load({'arr': [1, 2, 3]})
        np.testing.assert_array_equal(obj.arr, np.array([1, 2, 3]))

    def test_dump(self):
        @s.seared
        class Obj(s.Seared):
            arr: np.ndarray = s.NDArray(required=True)

        obj = Obj(arr=np.array([1, 2, 3]))
        d = Obj.dump(obj)
        assert d == {'arr': [1, 2, 3]}

    def test_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            arr: np.ndarray = s.NDArray(required=True)

        obj = Obj.load({'arr': [4, 5, 6]})
        d = Obj.dump(obj)
        assert d == {'arr': [4, 5, 6]}

    def test_2d_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            matrix: np.ndarray = s.NDArray(required=True)

        obj = Obj.load({'matrix': [[1, 2], [3, 4]]})
        d = Obj.dump(obj)
        assert d == {'matrix': [[1, 2], [3, 4]]}

    def test_optional_none_excluded_from_dump(self):
        @s.seared
        class Obj(s.Seared):
            arr: np.ndarray | None = s.NDArray()

        d = Obj.dump(Obj(arr=None))
        assert 'arr' not in d

    def test_many_load(self):
        @s.seared
        class Obj(s.Seared):
            arrays: list = s.NDArray(many=True, required=True)

        obj = Obj.load({'arrays': [[1, 2], [3, 4]]})
        assert len(obj.arrays) == 2
        np.testing.assert_array_equal(obj.arrays[0], np.array([1, 2]))
        np.testing.assert_array_equal(obj.arrays[1], np.array([3, 4]))

    def test_many_dump(self):
        @s.seared
        class Obj(s.Seared):
            arrays: list = s.NDArray(many=True, required=True)

        obj = Obj(arrays=[np.array([1, 2]), np.array([3, 4])])
        d = Obj.dump(obj)
        assert d == {'arrays': [[1, 2], [3, 4]]}

    def test_many_dump_called_multiple_times(self):
        """Regression: counter went out-of-bounds on second call."""

        @s.seared
        class Obj(s.Seared):
            arrays: list = s.NDArray(many=True, required=True)

        obj = Obj(arrays=[np.array([10, 20]), np.array([30, 40])])
        d1 = Obj.dump(obj)
        d2 = Obj.dump(obj)
        assert d1 == d2 == {'arrays': [[10, 20], [30, 40]]}


@s.seared
class Typed(s.Seared):
    f32: np.ndarray | None = s.NDArray(dtype='float32', default=None)
    i32: np.ndarray | None = s.NDArray(dtype=np.int32, default=None)
    i8: np.ndarray | None = s.NDArray(dtype='int8', default=None)
    flags: np.ndarray | None = s.NDArray(dtype=bool, default=None)
    many: list | None = s.NDArray(dtype='float32', many=True, default=None)


@s.seared(validate=False)
class LaxTyped(s.Seared):
    i8: np.ndarray | None = s.NDArray(dtype='int8', default=None)


class TestDtype:
    """``NDArray(dtype=…)`` casts each load and checks each strict dump (0.4.1)."""

    def test_dtype_takes_whatever_numpy_does_and_resolves_it(self):
        assert s.NDArray(dtype='float32').dtype == np.dtype(np.float32)
        assert s.NDArray(dtype=np.int32).dtype == np.dtype('int32')
        assert s.NDArray().dtype is None

    def test_a_dtype_numpy_doesnt_know_is_refused(self):
        with pytest.raises(TypeError, match="NDArray: dtype= takes a numpy dtype, got 'nope'"):
            s.NDArray(dtype='nope')

    def test_without_a_dtype_it_is_inferred_as_before(self):
        @s.seared
        class Plain(s.Seared):
            arr: np.ndarray = s.NDArray(required=True)

        assert Plain.load({'arr': [1.5]}).arr.dtype == np.float64

    def test_a_load_casts_to_the_dtype(self):
        loaded = Typed.load({'f32': [[0.5, 2.5]], 'i32': [1, 2.0, 3], 'i8': [-128, 127], 'flags': [0, 1, True]})
        assert (loaded.f32.dtype, loaded.i32.dtype, loaded.i8.dtype, loaded.flags.dtype) == (
            np.float32,
            np.int32,
            np.int8,
            np.bool_,
        )
        assert loaded.i32.tolist() == [1, 2, 3]
        assert loaded.flags.tolist() == [False, True, True]

    def test_a_float32_array_round_trips_exactly(self):
        values = np.array([0.1, 1 / 3, 1e-7], dtype=np.float32)
        back = Typed.load(Typed.dump(Typed(f32=values))).f32
        assert back.dtype == np.float32
        np.testing.assert_array_equal(back, values)

    def test_each_element_of_a_many_field_is_cast(self):
        loaded = Typed.load({'many': [[1.5], [2.5, 3.5]]})
        assert [a.dtype for a in loaded.many] == [np.float32, np.float32]

    def test_numeric_strings_cast_as_the_scalar_fields_take_them(self):
        assert Typed.load({'i32': ['1', '2']}).i32.tolist() == [1, 2]

    @pytest.mark.parametrize(
        ('data', 'message'),
        [
            ({'i32': [[1, 2], [3, 1.5]]}, r'^Typed\.i32\[1\]\[1\]: cannot deserialize 1\.5 as int32$'),
            ({'i32': [float('nan')]}, r'^Typed\.i32\[0\]: cannot deserialize nan as int32$'),
            ({'i8': [1, 300]}, r'^Typed\.i8\[1\]: cannot deserialize 300 as int8$'),
            ({'i8': [-129.0]}, r'^Typed\.i8\[0\]: cannot deserialize -129\.0 as int8$'),
            ({'i32': [True, False]}, r'^Typed\.i32: expected numbers, got bool, for dtype int32$'),
            ({'f32': [True]}, r'^Typed\.f32: expected numbers, got bool, for dtype float32$'),
            ({'f32': [1.0, 1e300]}, r'^Typed\.f32\[1\]: cannot deserialize 1e\+300 as float32$'),
            ({'flags': [0, 2]}, r'^Typed\.flags\[1\]: cannot deserialize 2 as bool$'),
            ({'i32': [2**70]}, r'^Typed\.i32: cannot deserialize as int32: '),
            ({'f32': ['x']}, r'^Typed\.f32: cannot deserialize as float32: '),
            ({'i32': [[1], [2, 3]]}, r'^Typed\.i32: cannot load as an array: '),
            ({'many': [[1.0], [1e300]]}, r'^Typed\.many\[1\]\[0\]: cannot deserialize 1e\+300 as float32$'),
        ],
    )
    def test_a_strict_load_refuses_what_it_cant_carry_over_whole(self, data, message):
        with pytest.raises(s.ValidationError, match=message):
            Typed.load(data)

    def test_a_bool_among_numbers_is_already_a_number(self):
        # The array, not each element, is what the cast sees, and numpy has made ``True`` a ``1``.
        assert Typed.load({'i32': [True, 2]}).i32.tolist() == [1, 2]

    def test_narrowing_a_floats_precision_is_allowed(self):
        assert Typed.load({'f32': [0.1]}).f32.tolist() == [np.float32(0.1).item()]

    def test_infinity_and_nan_stay_what_they_are_in_a_float(self):
        loaded = Typed.load({'f32': [float('inf'), float('nan')]}).f32
        assert np.isinf(loaded[0])
        assert np.isnan(loaded[1])

    def test_a_lax_load_casts_as_numpy_does(self):
        assert LaxTyped.load({'i8': [1.7, -3.2]}).i8.tolist() == [1, -3]

    def test_a_strict_dump_refuses_another_dtype(self):
        with pytest.raises(s.ValidationError, match=r'^Typed\.f32: expected dtype float32, got float64$'):
            Typed.dump(Typed(f32=np.array([1.5])))

    def test_a_strict_dump_of_the_declared_dtype_writes_lists(self):
        assert Typed.dump(Typed(f32=np.array([1.5], dtype=np.float32))) == {'f32': [1.5]}

    def test_a_lax_dump_casts_first(self):
        assert LaxTyped.dump(LaxTyped(i8=np.array([1.9, 2.1]))) == {'i8': [1, 2]}
