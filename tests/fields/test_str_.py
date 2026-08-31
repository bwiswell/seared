from __future__ import annotations

import pytest

import seared as s


class TestStr:
    @pytest.fixture
    def cls(self):
        @s.seared
        class Obj(s.Seared):
            name: str = s.Str(required=True)
            alias: str | None = s.Str(data_key='alias_key')

        return Obj

    def test_load(self, cls):
        obj = cls.load({'name': 'Alice', 'alias_key': 'Al'})
        assert obj.name == 'Alice'
        assert obj.alias == 'Al'

    def test_dump(self, cls):
        d = cls.dump(cls(name='Alice', alias='Al'))
        assert d == {'name': 'Alice', 'alias_key': 'Al'}

    def test_missing_optional_absent_from_dump(self, cls):
        d = cls.dump(cls(name='Bob', alias=None))
        assert 'alias_key' not in d

    def test_data_key_used_for_load(self, cls):
        obj = cls.load({'name': 'X', 'alias_key': 'Y'})
        assert obj.alias == 'Y'

    def test_data_key_used_for_dump(self, cls):
        d = cls.dump(cls(name='X', alias='Y'))
        assert 'alias_key' in d
        assert 'alias' not in d

    def test_many_load(self):
        @s.seared
        class Obj(s.Seared):
            tags: list = s.Str(many=True, required=True)

        obj = Obj.load({'tags': ['a', 'b', 'c']})
        assert obj.tags == ['a', 'b', 'c']

    def test_many_dump(self):
        @s.seared
        class Obj(s.Seared):
            tags: list = s.Str(many=True, required=True)

        d = Obj.dump(Obj(tags=['a', 'b', 'c']))
        assert d == {'tags': ['a', 'b', 'c']}

    def test_keyed_load(self):
        @s.seared
        class Obj(s.Seared):
            mapping: dict = s.Str(keyed=True, required=True)

        obj = Obj.load({'mapping': {'x': 'hello', 'y': 'world'}})
        assert obj.mapping == {'x': 'hello', 'y': 'world'}

    def test_keyed_dump(self):
        @s.seared
        class Obj(s.Seared):
            mapping: dict = s.Str(keyed=True, required=True)

        d = Obj.dump(Obj(mapping={'x': 'hello', 'y': 'world'}))
        assert d == {'mapping': {'x': 'hello', 'y': 'world'}}
