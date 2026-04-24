from __future__ import annotations

from typing import Optional

import seared as s


@s.seared
class Inner(s.Seared):
    x: int = s.Int(required=True)
    label: Optional[str] = s.Str()


class TestT:
    def test_simple_load(self):
        @s.seared
        class Outer(s.Seared):
            inner: Inner = s.T(schema=Inner.SCHEMA, required=True)

        obj = Outer.load({'inner': {'x': 5, 'label': 'hi'}})
        assert isinstance(obj.inner, Inner)
        assert obj.inner.x == 5
        assert obj.inner.label == 'hi'

    def test_simple_dump(self):
        @s.seared
        class Outer(s.Seared):
            inner: Inner = s.T(schema=Inner.SCHEMA, required=True)

        obj = Outer(inner=Inner(x=5, label='hi'))
        d = Outer.dump(obj)
        assert d == {'inner': {'x': 5, 'label': 'hi'}}

    def test_simple_round_trip(self):
        @s.seared
        class Outer(s.Seared):
            inner: Inner = s.T(schema=Inner.SCHEMA, required=True)

        raw = {'inner': {'x': 7}}
        obj = Outer.load(raw)
        assert Outer.dump(obj)['inner']['x'] == 7

    def test_optional_none_excluded_from_dump(self):
        @s.seared
        class Outer(s.Seared):
            inner: Optional[Inner] = s.T(schema=Inner.SCHEMA)

        d = Outer.dump(Outer(inner=None))
        assert 'inner' not in d

    def test_many_load(self):
        @s.seared
        class Outer(s.Seared):
            items: list = s.T(schema=Inner.SCHEMA, many=True, required=True)

        obj = Outer.load({'items': [{'x': 1}, {'x': 2, 'label': 'b'}]})
        assert len(obj.items) == 2
        assert obj.items[0].x == 1
        assert obj.items[1].x == 2
        assert obj.items[1].label == 'b'

    def test_many_dump(self):
        @s.seared
        class Outer(s.Seared):
            items: list = s.T(schema=Inner.SCHEMA, many=True, required=True)

        obj = Outer(items=[Inner(x=1, label=None), Inner(x=2, label='b')])
        d = Outer.dump(obj)
        assert d['items'][0] == {'x': 1}
        assert d['items'][1] == {'x': 2, 'label': 'b'}

    def test_many_round_trip(self):
        @s.seared
        class Outer(s.Seared):
            items: list = s.T(schema=Inner.SCHEMA, many=True, required=True)

        raw = {'items': [{'x': 3}, {'x': 4, 'label': 'four'}]}
        obj = Outer.load(raw)
        d = Outer.dump(obj)
        assert d['items'][0] == {'x': 3}
        assert d['items'][1] == {'x': 4, 'label': 'four'}

    def test_keyed_load(self):
        @s.seared
        class Outer(s.Seared):
            mapping: dict = s.T(schema=Inner.SCHEMA, keyed=True, required=True)

        obj = Outer.load({'mapping': {'a': {'x': 10}, 'b': {'x': 20, 'label': 'b'}}})
        assert obj.mapping['a'].x == 10
        assert obj.mapping['b'].x == 20

    def test_keyed_dump(self):
        @s.seared
        class Outer(s.Seared):
            mapping: dict = s.T(schema=Inner.SCHEMA, keyed=True, required=True)

        obj = Outer(mapping={'a': Inner(x=10, label=None), 'b': Inner(x=20, label='b')})
        d = Outer.dump(obj)
        assert d['mapping']['a'] == {'x': 10}
        assert d['mapping']['b'] == {'x': 20, 'label': 'b'}

    def test_keyed_round_trip(self):
        @s.seared
        class Outer(s.Seared):
            mapping: dict = s.T(schema=Inner.SCHEMA, keyed=True, required=True)

        raw = {'mapping': {'p': {'x': 1}, 'q': {'x': 2, 'label': 'q'}}}
        obj = Outer.load(raw)
        d = Outer.dump(obj)
        assert d['mapping']['p'] == {'x': 1}
        assert d['mapping']['q'] == {'x': 2, 'label': 'q'}

    def test_accepts_class_directly(self):
        @s.seared
        class Outer(s.Seared):
            inner: Inner = s.T(Inner, required=True)

        obj = Outer.load({'inner': {'x': 42}})
        assert obj.inner.x == 42
        assert Outer.dump(obj) == {'inner': {'x': 42}}

    def test_data_key(self):
        @s.seared
        class Outer(s.Seared):
            inner: Inner = s.T(schema=Inner.SCHEMA, data_key='nested', required=True)

        obj = Outer.load({'nested': {'x': 99}})
        assert obj.inner.x == 99
        d = Outer.dump(obj)
        assert 'nested' in d
        assert 'inner' not in d
