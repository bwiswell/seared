from __future__ import annotations

import json
from typing import Optional

import pytest

import seared as s
from conftest import Color


class TestSearedDecorator:
    def test_creates_dataclass(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True)

        f = Foo(x=42)
        assert f.x == 42

    def test_has_load(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True)

        f = Foo.load({'x': 7})
        assert isinstance(f, Foo)
        assert f.x == 7

    def test_has_dump(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True)

        d = Foo.dump(Foo(x=7))
        assert d == {'x': 7}

    def test_has_loads_and_dumps(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True)

        raw = '{"x": 7}'
        f = Foo.loads(raw)
        assert f.x == 7
        assert json.loads(Foo.dumps(f)) == {'x': 7}

    def test_has_schema(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True)

        from marshmallow import Schema
        assert isinstance(Foo.SCHEMA, Schema)

    def test_none_values_excluded_from_dump(self):
        @s.seared
        class Foo(s.Seared):
            x: Optional[int] = s.Int()

        d = Foo.dump(Foo(x=None))
        assert 'x' not in d

    def test_unknown_keys_excluded_on_load(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True)

        f = Foo.load({'x': 1, 'unknown_key': 'garbage'})
        assert f.x == 1

    def test_dump_false_field_excluded_from_dump(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True)
            password: str = s.Str(required=True, dump=False)

        f = Foo.load({'x': 1, 'password': 'secret'})
        assert f.password == 'secret'
        d = Foo.dump(f)
        assert 'password' not in d
        assert d == {'x': 1}


class TestMixedClass:
    def test_readme_example(self):
        @s.seared
        class A(s.Seared):
            a: Optional[int]   = s.Int(data_key='propertyA')
            b: Optional[float] = s.Float(data_key='propertyB')
            c: Optional[str]   = s.Str(data_key='propertyC')

        @s.seared
        class B(s.Seared):
            a: int   = s.Int(missing=5)
            b: float = s.Float(missing=3.14)
            c: str   = s.Str(missing='hello')
            d: A     = s.T(A.SCHEMA, required=True)
            e: Color = s.Enum(enum=Color, missing=Color.GREEN)
            f: list  = s.Int(many=True, missing=[])
            g: dict  = s.Float(keyed=True, missing={})

        data = {
            'a': 3,
            'c': 'world',
            'd': {'propertyA': 5},
            'e': 2,
            'f': [3, 7, 4, 1],
            'g': {'x': 3.5, 'y': 1.6},
        }

        obj = B.load(data)
        assert obj.a == 3
        assert obj.c == 'world'
        assert obj.d.a == 5
        assert obj.e == Color.BLUE
        assert obj.f == [3, 7, 4, 1]
        assert abs(obj.g['x'] - 3.5) < 1e-9

        out = B.dump(obj)
        assert out['a'] == 3
        assert out['e'] == 2
        assert out['f'] == [3, 7, 4, 1]
        assert out['d']['propertyA'] == 5

    def test_deeply_nested_round_trip(self):
        @s.seared
        class Leaf(s.Seared):
            val: int = s.Int(required=True)

        @s.seared
        class Mid(s.Seared):
            leaf: Leaf = s.T(schema=Leaf.SCHEMA, required=True)
            tag: str   = s.Str(required=True)

        @s.seared
        class Root(s.Seared):
            mid: Mid = s.T(schema=Mid.SCHEMA, required=True)

        raw = {'mid': {'leaf': {'val': 42}, 'tag': 'hello'}}
        obj = Root.load(raw)
        assert obj.mid.leaf.val == 42
        assert obj.mid.tag == 'hello'
        d = Root.dump(obj)
        assert d == raw


def test_version():
    assert s.__version__ == '0.2.0'
