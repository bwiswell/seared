from __future__ import annotations

import seared as s


class TestTuple:
    def test_load(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple = s.Tuple(s.Float(), s.Float(), required=True)

        obj = Obj.load({'point': [1.0, 2.0]})
        assert obj.point == (1.0, 2.0)

    def test_dump(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple = s.Tuple(s.Float(), s.Float(), required=True)

        d = Obj.dump(Obj(point=(1.0, 2.0)))
        # Tuple serialises to a Python tuple; JSON output is a list
        assert d['point'] == (1.0, 2.0)

    def test_json_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple = s.Tuple(s.Float(), s.Float(), required=True)

        obj = Obj.loads(Obj.dumps(Obj(point=(3.14, 2.72))))
        assert obj.point == (3.14, 2.72)

    def test_mixed_types(self):
        @s.seared
        class Obj(s.Seared):
            record: tuple = s.Tuple(s.Str(), s.Int(), s.Bool(), required=True)

        obj = Obj.load({'record': ['alice', 42, True]})
        assert obj.record == ('alice', 42, True)
        assert Obj.dump(obj)['record'] == ('alice', 42, True)

    def test_single_element(self):
        @s.seared
        class Obj(s.Seared):
            wrap: tuple = s.Tuple(s.Int(), required=True)

        obj = Obj.load({'wrap': [7]})
        assert obj.wrap == (7,)
        assert Obj.dump(obj)['wrap'] == (7,)

    def test_optional_none_excluded_from_dump(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple | None = s.Tuple(s.Float(), s.Float())

        d = Obj.dump(Obj(point=None))
        assert 'point' not in d

    def test_missing_default(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple = s.Tuple(s.Float(), s.Float(), missing=(0.0, 0.0))

        obj = Obj.load({})
        assert obj.point == (0.0, 0.0)

    def test_many_load(self):
        @s.seared
        class Obj(s.Seared):
            points: list = s.Tuple(s.Float(), s.Float(), many=True, required=True)

        obj = Obj.load({'points': [[1.0, 2.0], [3.0, 4.0]]})
        assert obj.points == [(1.0, 2.0), (3.0, 4.0)]

    def test_many_json_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            points: list = s.Tuple(s.Float(), s.Float(), many=True, required=True)

        obj = Obj.loads(Obj.dumps(Obj(points=[(1.0, 2.0), (3.0, 4.0)])))
        assert obj.points == [(1.0, 2.0), (3.0, 4.0)]

    def test_data_key(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple = s.Tuple(s.Float(), s.Float(), data_key='coords', required=True)

        obj = Obj.load({'coords': [5.0, 6.0]})
        assert obj.point == (5.0, 6.0)
        d = Obj.dump(obj)
        assert 'coords' in d
        assert 'point' not in d
