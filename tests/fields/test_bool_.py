from __future__ import annotations

import seared as s


class TestBool:
    def test_load_and_dump(self):
        @s.seared
        class Obj(s.Seared):
            flag: bool = s.Bool(required=True)

        obj = Obj.load({'flag': True})
        assert obj.flag is True
        assert Obj.dump(obj) == {'flag': True}

    def test_false_value_preserved_in_dump(self):
        @s.seared
        class Obj(s.Seared):
            flag: bool = s.Bool(required=True)

        d = Obj.dump(Obj(flag=False))
        assert d['flag'] is False

    def test_many_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            flags: list = s.Bool(many=True, required=True)

        obj = Obj.load({'flags': [True, False, True]})
        assert obj.flags == [True, False, True]
        assert Obj.dump(obj) == {'flags': [True, False, True]}
