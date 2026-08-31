from __future__ import annotations

import uuid

import seared as s

_UUID_A = uuid.UUID('12345678-1234-5678-1234-567812345678')
_UUID_B = uuid.UUID('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')


class TestUUID:
    def test_load(self):
        @s.seared
        class Obj(s.Seared):
            uid: uuid.UUID = s.UUID(required=True)

        obj = Obj.load({'uid': str(_UUID_A)})
        assert obj.uid == _UUID_A

    def test_dump(self):
        @s.seared
        class Obj(s.Seared):
            uid: uuid.UUID = s.UUID(required=True)

        d = Obj.dump(Obj(uid=_UUID_A))
        assert d == {'uid': str(_UUID_A)}

    def test_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            uid: uuid.UUID = s.UUID(required=True)

        raw = {'uid': str(_UUID_B)}
        obj = Obj.load(raw)
        assert Obj.dump(obj) == raw

    def test_optional_none_excluded_from_dump(self):
        @s.seared
        class Obj(s.Seared):
            uid: uuid.UUID | None = s.UUID()

        d = Obj.dump(Obj(uid=None))
        assert 'uid' not in d

    def test_missing_default(self):
        @s.seared
        class Obj(s.Seared):
            uid: uuid.UUID = s.UUID(missing=_UUID_A)

        obj = Obj.load({})
        assert obj.uid == _UUID_A

    def test_many_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            ids: list = s.UUID(many=True, required=True)

        raw = {'ids': [str(_UUID_A), str(_UUID_B)]}
        obj = Obj.load(raw)
        assert obj.ids == [_UUID_A, _UUID_B]
        assert Obj.dump(obj) == raw
