from __future__ import annotations

import seared as s


class TestInt:
    def test_load_and_dump(self):
        @s.seared
        class Obj(s.Seared):
            val: int = s.Int(required=True)

        obj = Obj.load({'val': 42})
        assert obj.val == 42
        assert Obj.dump(obj) == {'val': 42}

    def test_missing_default(self):
        @s.seared
        class Obj(s.Seared):
            val: int = s.Int(missing=0)

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
