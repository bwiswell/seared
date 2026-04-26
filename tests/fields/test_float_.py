from __future__ import annotations

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
