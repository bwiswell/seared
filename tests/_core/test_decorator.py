"""Tests for ``seared._core.decorator`` — the ``@seared`` decorator
that turns a class into a serialisable dataclass.

Folds in three feature suites that hammer different parts of the
decorator's responsibilities:

- ``test_mutable_defaults`` — deep-copy semantics for mutable
  ``missing`` defaults (the decorator wraps ``__init__``).
- ``test_multi_union`` — multi-``Union`` collision-detection that
  ``_build`` performs at class-creation time.
- ``test_binary_format`` — ``format=`` kwarg threading through
  ``dump``/``load`` into each field's ``serialize``/``deserialize``.
"""
from __future__ import annotations

import json

import pytest
from conftest import Color

import seared as s

# ---------------------------------------------------------------------------
# Decorator basics — class gets dump/load/loads/dumps + __seared_fields__.
# ---------------------------------------------------------------------------

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

    def test_has_seared_fields(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True)

        assert isinstance(Foo.__seared_fields__, tuple)
        assert len(Foo.__seared_fields__) == 1
        attr, wire, field = Foo.__seared_fields__[0]
        assert attr == 'x'
        assert wire == 'x'
        assert isinstance(field, s.Int)

    def test_natural_init_replaces_field_defaults_with_missing(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True)
            y: int | None = s.Int()
            z: int = s.Int(missing=42)

        f = Foo(x=1)
        assert f.y is None
        assert f.z == 42
        assert Foo.dump(f) == {'x': 1, 'z': 42}

    def test_none_values_excluded_from_dump(self):
        @s.seared
        class Foo(s.Seared):
            x: int | None = s.Int()

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
            a: int | None   = s.Int(data_key='propertyA')
            b: float | None = s.Float(data_key='propertyB')
            c: str | None   = s.Str(data_key='propertyC')

        @s.seared
        class B(s.Seared):
            a: int   = s.Int(missing=5)
            b: float = s.Float(missing=3.14)
            c: str   = s.Str(missing='hello')
            d: A     = s.T(A, required=True)
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
            leaf: Leaf = s.T(schema=Leaf, required=True)
            tag: str   = s.Str(required=True)

        @s.seared
        class Root(s.Seared):
            mid: Mid = s.T(schema=Mid, required=True)

        raw = {'mid': {'leaf': {'val': 42}, 'tag': 'hello'}}
        obj = Root.load(raw)
        assert obj.mid.leaf.val == 42
        assert obj.mid.tag == 'hello'
        d = Root.dump(obj)
        assert d == raw


# ---------------------------------------------------------------------------
# Mutable ``missing`` defaults — deep-copied per instance (was
# tests/test_mutable_defaults.py).
# ---------------------------------------------------------------------------

class TestListMissing:
    def test_two_instances_have_distinct_lists(self):
        @s.seared
        class Bag(s.Seared):
            tags: list = s.Str(many=True, missing=[])

        a = Bag()
        b = Bag()
        a.tags.append('one')
        # Pre-fix: b.tags would also contain 'one' (same list object).
        assert b.tags == [], (
            'mutable-default fix regressed — instances are sharing the list'
        )
        assert a.tags == ['one']

    def test_explicit_value_unaffected(self):
        @s.seared
        class Bag(s.Seared):
            tags: list = s.Str(many=True, missing=[])

        explicit = ['a', 'b']
        a = Bag(tags=explicit)
        # Mutating the original list passed in changes a.tags (we don't
        # copy explicit user values; only missing-defaults).
        explicit.append('c')
        assert a.tags == ['a', 'b', 'c']     # documented passthrough


class TestDictMissing:
    def test_two_instances_have_distinct_dicts(self):
        @s.seared
        class Doc(s.Seared):
            meta: dict = s.Str(keyed=True, missing={})

        a = Doc()
        b = Doc()
        a.meta['key'] = 'value'
        assert b.meta == {}, 'dict missing-default sharing regressed'

    def test_nested_mutable_isolated_via_deepcopy(self):
        """Pin deepcopy semantics: ``missing={'tags': ['default']}``
        gives each instance its own OUTER dict AND its own INNER list.
        With shallow copy, the inner list would be shared."""
        @s.seared
        class Doc(s.Seared):
            meta: dict = s.Dict(missing={'tags': ['default']})

        a = Doc()
        b = Doc()
        a.meta['tags'].append('shared?')
        assert b.meta == {'tags': ['default']}, (
            'nested mutable inside missing-default got shared — deepcopy '
            'failed to isolate the inner list'
        )


class TestSetMissing:
    def test_two_instances_have_distinct_sets(self):
        # No ``Set`` field type in seared; use ``Str(many=True)`` plus
        # a ``set`` missing — the decorator's wrapper deepcopies the
        # raw missing object regardless of the field's wire shape.
        @s.seared
        class Tags(s.Seared):
            members: set = s.Str(many=True, missing=set())

        a = Tags()
        b = Tags()
        a.members.add('alpha')
        assert b.members == set()


class TestFrozensetMissing:
    def test_frozenset_missing_deep_copied(self):
        @s.seared
        class Tags(s.Seared):
            members: frozenset = s.Str(many=True, missing=frozenset())

        a = Tags()
        b = Tags()
        # Frozenset is immutable; both should be empty, equal.
        assert a.members == b.members == frozenset()


class TestImmutableMissing:
    def test_string_missing_passthrough(self):
        @s.seared
        class Doc(s.Seared):
            tag: str = s.Str(missing='default')

        a = Doc()
        b = Doc()
        # Strings are immutable; both share the same object — fine.
        assert a.tag == b.tag == 'default'

    def test_int_missing_passthrough(self):
        @s.seared
        class Counter(s.Seared):
            n: int = s.Int(missing=0)

        a = Counter()
        b = Counter()
        assert a.n == b.n == 0

    def test_none_missing_passthrough(self):
        @s.seared
        class Maybe(s.Seared):
            value: object = s.Str(missing=None)

        a = Maybe()
        assert a.value is None


# ---------------------------------------------------------------------------
# Multi-Union fields — disjoint-key validation in ``_build`` (was
# tests/test_multi_union.py).
# ---------------------------------------------------------------------------

@s.seared
class _Up(s.Seared):
    speed: int = s.Int(required=True)


@s.seared
class _Down(s.Seared):
    reason: str = s.Str(missing='')


@s.seared
class _Read(s.Seared):
    keys: list = s.Str(many=True, missing=[])


@s.seared
class _Write(s.Seared):
    payload: str = s.Str(required=True)


class TestDisjointUnions:
    def test_two_unions_with_distinct_keys(self):
        @s.seared
        class Cmd(s.Seared):
            # Two UNWRAP fields — disjoint discriminator keys.
            motion: object = s.Union(
                variants={'up': _Up, 'down': _Down},
                tag_key='motion_type',
            )
            io: object = s.Union(
                variants={'read': _Read, 'write': _Write},
                tag_key='io_type',
            )

        cmd = Cmd(
            motion=_Up(speed=10),
            io=_Read(keys=['a', 'b']),
        )
        d = Cmd.dump(cmd)
        assert d['motion_type'] == 'up'
        assert d['io_type'] == 'read'
        assert d['speed'] == 10
        assert d['keys'] == ['a', 'b']

        loaded = Cmd.load(d)
        assert isinstance(loaded.motion, _Up)
        assert isinstance(loaded.io, _Read)
        assert loaded.motion.speed == 10
        assert loaded.io.keys == ['a', 'b']

    def test_disjoint_with_payload_keys(self):
        @s.seared
        class Wrapped(s.Seared):
            a: object = s.Union(
                variants={'up': _Up, 'down': _Down},
                tag_key='a_type',
                payload_key='a_payload',
            )
            b: object = s.Union(
                variants={'read': _Read, 'write': _Write},
                tag_key='b_type',
                payload_key='b_payload',
            )

        obj = Wrapped(a=_Up(speed=5), b=_Write(payload='hi'))
        d = Wrapped.dump(obj)
        loaded = Wrapped.load(d)
        assert isinstance(loaded.a, _Up)
        assert isinstance(loaded.b, _Write)


class TestKeyCollisionRejected:
    def test_shared_tag_key_raises(self):
        with pytest.raises(TypeError, match='share wire key'):
            @s.seared
            class Bad(s.Seared):
                a: object = s.Union(
                    variants={'up': _Up}, tag_key='type',
                )
                b: object = s.Union(
                    variants={'read': _Read}, tag_key='type',  # collision
                )

    def test_tag_payload_key_collision(self):
        """A's tag_key collides with B's payload_key — also rejected."""
        with pytest.raises(TypeError, match='share wire key'):
            @s.seared
            class Bad(s.Seared):
                a: object = s.Union(
                    variants={'up': _Up}, tag_key='kind',
                )
                b: object = s.Union(
                    variants={'read': _Read},
                    tag_key='b_type',
                    payload_key='kind',                       # collision
                )

    def test_default_tag_key_is_collision(self):
        """Two Unions both using the default ``tag_key='type'`` collide."""
        with pytest.raises(TypeError, match='share wire key'):
            @s.seared
            class Bad(s.Seared):
                a: object = s.Union(variants={'up': _Up})
                b: object = s.Union(variants={'read': _Read})


class TestSingleUnionUnchanged:
    """Existing single-Union semantics still work — no regression."""
    def test_single_unwrap_field(self):
        @s.seared
        class Cmd(s.Seared):
            action: object = s.Union(variants={'up': _Up, 'down': _Down})

        cmd = Cmd(action=_Up(speed=20))
        d = Cmd.dump(cmd)
        assert d == {'type': 'up', 'speed': 20}
        loaded = Cmd.load(d)
        assert isinstance(loaded.action, _Up)


# ---------------------------------------------------------------------------
# ``format=`` carrier-hint threading through dump / load (was
# tests/test_binary_format.py). Asserts the decorator passes ``format=``
# down into each field's serialize / deserialize.
# ---------------------------------------------------------------------------

@s.seared
class _Blob(s.Seared):
    payload: bytes = s.Bytes(required=True)


@s.seared
class _Many(s.Seared):
    chunks: list = s.Bytes(many=True, missing=[])


class TestJSONDefault:
    def test_default_serializes_to_base64_string(self):
        b = _Blob(payload=b'hello')
        d = _Blob.dump(b)
        assert d == {'payload': 'aGVsbG8='}     # base64 of 'hello'
        assert isinstance(d['payload'], str)

    def test_default_deserializes_from_base64_string(self):
        loaded = _Blob.load({'payload': 'aGVsbG8='})
        assert loaded.payload == b'hello'

    def test_explicit_json_format_kwarg(self):
        b = _Blob(payload=b'world')
        d = _Blob.dump(b, format='json')
        assert d == {'payload': 'd29ybGQ='}
        loaded = _Blob.load(d, format='json')
        assert loaded.payload == b'world'


class TestMsgpackFormat:
    def test_serializes_native_bytes_under_msgpack(self):
        b = _Blob(payload=b'binary-data')
        d = _Blob.dump(b, format='msgpack')
        assert d == {'payload': b'binary-data'}
        assert isinstance(d['payload'], bytes)

    def test_deserializes_native_bytes_under_msgpack(self):
        loaded = _Blob.load({'payload': b'binary-data'}, format='msgpack')
        assert loaded.payload == b'binary-data'

    def test_round_trip_lossless(self):
        original = bytes(range(256))     # all byte values
        b = _Blob(payload=original)
        d = _Blob.dump(b, format='msgpack')
        loaded = _Blob.load(d, format='msgpack')
        assert loaded.payload == original

    def test_many_under_msgpack(self):
        m = _Many(chunks=[b'one', b'two', b'three'])
        d = _Many.dump(m, format='msgpack')
        assert d == {'chunks': [b'one', b'two', b'three']}
        for chunk in d['chunks']:
            assert isinstance(chunk, bytes)
        loaded = _Many.load(d, format='msgpack')
        assert loaded.chunks == [b'one', b'two', b'three']


class TestFormatPassesThroughOtherFields:
    """Pin: non-binary fields (``Str``, ``Int``, etc.) accept the
    ``format=`` kwarg without complaint and produce identical output
    regardless of carrier."""
    def test_string_field_unaffected(self):
        @s.seared
        class M(s.Seared):
            name: str = s.Str(required=True)

        m = M(name='alice')
        json_dump = M.dump(m, format='json')
        msgpack_dump = M.dump(m, format='msgpack')
        # Non-binary fields produce identical output for both carriers.
        assert json_dump == msgpack_dump == {'name': 'alice'}
