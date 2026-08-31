from __future__ import annotations

import pytest

import seared as s


class TestDict:
    @pytest.fixture
    def cls(self):
        @s.seared
        class Obj(s.Seared):
            meta: dict = s.Dict(required=True)
            extras: dict | None = s.Dict(data_key='extra_data')

        return Obj

    def test_load(self, cls):
        obj = cls.load(
            {
                'meta': {'name': 'widget', 'count': 3},
                'extra_data': {'nested': {'k': 'v'}, 'num': 1},
            }
        )
        assert obj.meta == {'name': 'widget', 'count': 3}
        assert obj.extras == {'nested': {'k': 'v'}, 'num': 1}

    def test_dump(self, cls):
        d = cls.dump(
            cls(
                meta={'name': 'widget', 'count': 3},
                extras={'foo': 'bar'},
            )
        )
        assert d == {
            'meta': {'name': 'widget', 'count': 3},
            'extra_data': {'foo': 'bar'},
        }

    def test_missing_optional_absent_from_dump(self, cls):
        d = cls.dump(cls(meta={'a': 1}, extras=None))
        assert 'extra_data' not in d
        assert d == {'meta': {'a': 1}}

    def test_data_key_used_for_load(self, cls):
        obj = cls.load({'meta': {}, 'extra_data': {'x': 1}})
        assert obj.extras == {'x': 1}

    def test_empty_dict_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            meta: dict = s.Dict(required=True)

        obj = Obj.load({'meta': {}})
        assert obj.meta == {}
        assert Obj.dump(obj) == {'meta': {}}

    def test_heterogeneous_values(self):
        @s.seared
        class Obj(s.Seared):
            meta: dict = s.Dict(required=True)

        raw = {'meta': {'s': 'hello', 'i': 7, 'f': 1.5, 'b': True, 'n': None, 'list': [1, 2, 3], 'nested': {'k': 'v'}}}
        obj = Obj.load(raw)
        assert Obj.dump(obj) == raw

    def test_missing_default(self):
        @s.seared
        class Obj(s.Seared):
            meta: dict = s.Dict(missing={})

        obj = Obj.load({})
        assert obj.meta == {}

    def test_many_load(self):
        @s.seared
        class Obj(s.Seared):
            records: list = s.Dict(many=True, required=True)

        obj = Obj.load({'records': [{'a': 1}, {'b': 2}]})
        assert obj.records == [{'a': 1}, {'b': 2}]

    def test_many_dump(self):
        @s.seared
        class Obj(s.Seared):
            records: list = s.Dict(many=True, required=True)

        d = Obj.dump(Obj(records=[{'a': 1}, {'b': 2}]))
        assert d == {'records': [{'a': 1}, {'b': 2}]}

    def test_keyed_load(self):
        @s.seared
        class Obj(s.Seared):
            groups: dict = s.Dict(keyed=True, required=True)

        obj = Obj.load({'groups': {'g1': {'x': 1}, 'g2': {'y': 2}}})
        assert obj.groups == {'g1': {'x': 1}, 'g2': {'y': 2}}

    def test_keyed_dump(self):
        @s.seared
        class Obj(s.Seared):
            groups: dict = s.Dict(keyed=True, required=True)

        d = Obj.dump(Obj(groups={'g1': {'x': 1}, 'g2': {'y': 2}}))
        assert d == {'groups': {'g1': {'x': 1}, 'g2': {'y': 2}}}
