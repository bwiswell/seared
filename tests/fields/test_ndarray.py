from __future__ import annotations

import numpy as np

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
