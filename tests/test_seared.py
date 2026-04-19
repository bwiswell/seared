"""
Comprehensive pytest suite for seared 0.2.1.

Covers:
- Every field type (Bool, Str, Int, Float, Date, DateTime, Time, Enum, Dict, NDArray, T)
- Both load (deserialise) and dump (serialise) directions
- Optional fields (missing=...), required fields, data_key renaming
- many=True (list) and keyed=True (dict) wrappers — regression for the
  Function-field serialize bugs that were present in 0.1.x
- Scalar and collection round-trips (load → dump → load produces same object)
- The @seared decorator: creates a proper frozen-ish dataclass with
  .load(), .dump(), .loads(), .dumps(), and .SCHEMA
"""
from __future__ import annotations

import json
from datetime import date, datetime, time
from enum import Enum
from typing import Optional

import numpy as np
import pytest

import seared as s


# ---------------------------------------------------------------------------
# Shared helpers / fixtures
# ---------------------------------------------------------------------------

class Color(Enum):
    RED   = 0
    GREEN = 1
    BLUE  = 2


class Status(str, Enum):
    ACTIVE   = 'active'
    INACTIVE = 'inactive'
    PENDING  = 'pending'


# ===========================================================================
# @seared decorator
# ===========================================================================

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


# ===========================================================================
# Str field
# ===========================================================================

class TestStr:
    @pytest.fixture
    def cls(self):
        @s.seared
        class Obj(s.Seared):
            name: str = s.Str(required=True)
            alias: Optional[str] = s.Str(data_key='alias_key')

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


# ===========================================================================
# Int field
# ===========================================================================

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


# ===========================================================================
# Float field
# ===========================================================================

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


# ===========================================================================
# Bool field
# ===========================================================================

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


# ===========================================================================
# Date field
# ===========================================================================

class TestDate:
    def test_load_and_dump(self):
        @s.seared
        class Obj(s.Seared):
            d: date = s.Date(required=True)

        obj = Obj.load({'d': '2025-01-15'})
        assert obj.d == date(2025, 1, 15)
        dumped = Obj.dump(obj)
        assert dumped['d'] == '2025-01-15'

    def test_custom_format(self):
        @s.seared
        class Obj(s.Seared):
            d: date = s.Date(format='%Y%m%d', required=True)

        obj = Obj.load({'d': '20250115'})
        assert obj.d == date(2025, 1, 15)
        dumped = Obj.dump(obj)
        assert dumped['d'] == '20250115'

    def test_many_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            dates: list = s.Date(many=True, required=True)

        obj = Obj.load({'dates': ['2025-01-01', '2025-06-15']})
        assert obj.dates == [date(2025, 1, 1), date(2025, 6, 15)]
        d = Obj.dump(obj)
        assert d['dates'] == ['2025-01-01', '2025-06-15']


# ===========================================================================
# DateTime field
# ===========================================================================

class TestDateTime:
    def test_load_and_dump(self):
        @s.seared
        class Obj(s.Seared):
            ts: datetime = s.DateTime(required=True)

        obj = Obj.load({'ts': '2025-01-15T08:30:00'})
        assert obj.ts == datetime(2025, 1, 15, 8, 30, 0)
        dumped = Obj.dump(obj)
        assert '2025-01-15' in dumped['ts']


# ===========================================================================
# Time field
# ===========================================================================

class TestTime:
    def test_load_and_dump(self):
        @s.seared
        class Obj(s.Seared):
            t: time = s.Time(required=True)

        obj = Obj.load({'t': '08:30:00'})
        assert obj.t == time(8, 30, 0)
        dumped = Obj.dump(obj)
        assert '08:30:00' in dumped['t']


# ===========================================================================
# Enum field — regression for Function-field serialize bug
# ===========================================================================

class TestEnum:
    @pytest.fixture
    def cls(self):
        @s.seared
        class Obj(s.Seared):
            color: Color = s.Enum(enum=Color, required=True)
            optional_color: Optional[Color] = s.Enum(
                enum=Color, missing=Color.RED
            )

        return Obj

    def test_load(self, cls):
        obj = cls.load({'color': 2})
        assert obj.color == Color.BLUE

    def test_load_string_value(self, cls):
        obj = cls.load({'color': '1'})
        assert obj.color == Color.GREEN

    def test_dump(self, cls):
        d = cls.dump(cls(color=Color.BLUE, optional_color=Color.GREEN))
        assert d['color'] == 2
        assert d['optional_color'] == 1

    def test_missing_default(self, cls):
        obj = cls.load({'color': 0})
        assert obj.optional_color == Color.RED

    def test_optional_none_excluded_from_dump(self):
        @s.seared
        class Obj(s.Seared):
            color: Optional[Color] = s.Enum(enum=Color)

        d = Obj.dump(Obj(color=None))
        assert 'color' not in d

    # Regression: many=True used Function which received parent object, not item
    def test_many_load(self):
        @s.seared
        class Obj(s.Seared):
            colors: list = s.Enum(enum=Color, many=True, required=True)

        obj = Obj.load({'colors': [0, 1, 2]})
        assert obj.colors == [Color.RED, Color.GREEN, Color.BLUE]

    def test_many_dump(self):
        @s.seared
        class Obj(s.Seared):
            colors: list = s.Enum(enum=Color, many=True, required=True)

        obj = Obj(colors=[Color.RED, Color.GREEN, Color.BLUE])
        d = Obj.dump(obj)
        assert d == {'colors': [0, 1, 2]}

    def test_many_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            colors: list = s.Enum(enum=Color, many=True, required=True)

        raw = {'colors': [2, 0, 1]}
        obj = Obj.load(raw)
        assert Obj.dump(obj) == raw

    def test_keyed_load(self):
        @s.seared
        class Obj(s.Seared):
            palette: dict = s.Enum(enum=Color, keyed=True, required=True)

        obj = Obj.load({'palette': {'bg': 0, 'fg': 2}})
        assert obj.palette == {'bg': Color.RED, 'fg': Color.BLUE}

    def test_keyed_dump(self):
        @s.seared
        class Obj(s.Seared):
            palette: dict = s.Enum(enum=Color, keyed=True, required=True)

        obj = Obj(palette={'bg': Color.RED, 'fg': Color.BLUE})
        d = Obj.dump(obj)
        assert d == {'palette': {'bg': 0, 'fg': 2}}

    # String-valued enum support (0.2.1)
    def test_str_enum_load(self):
        @s.seared
        class Obj(s.Seared):
            status: Status = s.Enum(enum=Status, required=True)

        obj = Obj.load({'status': 'active'})
        assert obj.status == Status.ACTIVE

    def test_str_enum_dump(self):
        @s.seared
        class Obj(s.Seared):
            status: Status = s.Enum(enum=Status, required=True)

        d = Obj.dump(Obj(status=Status.PENDING))
        assert d == {'status': 'pending'}

    def test_str_enum_missing_default(self):
        @s.seared
        class Obj(s.Seared):
            status: Optional[Status] = s.Enum(
                enum=Status, missing=Status.INACTIVE
            )

        obj = Obj.load({})
        assert obj.status == Status.INACTIVE

    def test_str_enum_many_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            statuses: list = s.Enum(enum=Status, many=True, required=True)

        raw = {'statuses': ['active', 'pending', 'inactive']}
        obj = Obj.load(raw)
        assert obj.statuses == [Status.ACTIVE, Status.PENDING, Status.INACTIVE]
        assert Obj.dump(obj) == raw

    def test_str_enum_keyed_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            mapping: dict = s.Enum(enum=Status, keyed=True, required=True)

        raw = {'mapping': {'a': 'active', 'b': 'pending'}}
        obj = Obj.load(raw)
        assert obj.mapping == {'a': Status.ACTIVE, 'b': Status.PENDING}
        assert Obj.dump(obj) == raw


# ===========================================================================
# Dict field
# ===========================================================================

class TestDict:
    @pytest.fixture
    def cls(self):
        @s.seared
        class Obj(s.Seared):
            meta: dict = s.Dict(required=True)
            extras: Optional[dict] = s.Dict(data_key='extra_data')

        return Obj

    def test_load(self, cls):
        obj = cls.load({
            'meta': {'name': 'widget', 'count': 3},
            'extra_data': {'nested': {'k': 'v'}, 'num': 1},
        })
        assert obj.meta == {'name': 'widget', 'count': 3}
        assert obj.extras == {'nested': {'k': 'v'}, 'num': 1}

    def test_dump(self, cls):
        d = cls.dump(cls(
            meta={'name': 'widget', 'count': 3},
            extras={'foo': 'bar'},
        ))
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

        raw = {'meta': {'s': 'hello', 'i': 7, 'f': 1.5, 'b': True, 'n': None,
                        'list': [1, 2, 3], 'nested': {'k': 'v'}}}
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


# ===========================================================================
# NDArray field — regression for counter-based serialize hack
# ===========================================================================

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
            arr: Optional[np.ndarray] = s.NDArray()

        d = Obj.dump(Obj(arr=None))
        assert 'arr' not in d

    # Regression: many=True used a counter `i` that broke on multiple dump calls
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
        """Regression: the old counter would go out-of-bounds on the second call."""
        @s.seared
        class Obj(s.Seared):
            arrays: list = s.NDArray(many=True, required=True)

        obj = Obj(arrays=[np.array([10, 20]), np.array([30, 40])])
        d1 = Obj.dump(obj)
        d2 = Obj.dump(obj)
        assert d1 == d2 == {'arrays': [[10, 20], [30, 40]]}


# ===========================================================================
# T field (nested schema) — regression for Function-field serialize bugs
# ===========================================================================

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

    # Regression: many=True produced [{}] instead of the actual nested dicts
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

    # Regression: keyed=True produced {} for each dict value
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

    def test_data_key(self):
        @s.seared
        class Outer(s.Seared):
            inner: Inner = s.T(schema=Inner.SCHEMA, data_key='nested', required=True)

        obj = Outer.load({'nested': {'x': 99}})
        assert obj.inner.x == 99
        d = Outer.dump(obj)
        assert 'nested' in d
        assert 'inner' not in d


# ===========================================================================
# Integration: mixed-field classes (mirrors README example)
# ===========================================================================

class TestMixedClass:
    def test_readme_example(self):
        @s.seared
        class A(s.Seared):
            a: Optional[int]   = s.Int(data_key='propertyA')
            b: Optional[float] = s.Float(data_key='propertyB')
            c: Optional[str]   = s.Str(data_key='propertyC')

        @s.seared
        class B(s.Seared):
            a: int          = s.Int(missing=5)
            b: float        = s.Float(missing=3.14)
            c: str          = s.Str(missing='hello')
            d: A            = s.T(A.SCHEMA, required=True)
            e: Color        = s.Enum(enum=Color, missing=Color.GREEN)
            f: list         = s.Int(many=True, missing=[])
            g: dict         = s.Float(keyed=True, missing={})

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
        """Nested T inside T should round-trip correctly."""
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


# ===========================================================================
# version
# ===========================================================================

def test_version():
    assert s.__version__ == '0.2.1'
