"""Tests for ``seared._core.decorator`` — the ``@seared`` decorator
that turns a class into a serialisable dataclass.

Folds in three feature suites that hammer different parts of the
decorator's responsibilities:

- ``test_mutable_defaults`` — deep-copy semantics for mutable
  ``default`` values (the decorator wraps ``__init__``).
- ``test_multi_union`` — multi-``Union`` collision-detection that
  ``_build`` performs at class-creation time.
- ``test_binary_format`` — ``format=`` kwarg threading through
  ``dump``/``load`` into each field's ``serialize``/``deserialize``.
"""

from __future__ import annotations

import builtins
import functools
import json
import operator
from dataclasses import InitVar  # noqa: TC003 — dataclass() resolves the string annotation at runtime

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

    def test_seared_fields_entries_are_field_specs(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True, data_key='ex')

        (spec,) = Foo.__seared_fields__
        assert isinstance(spec, s.FieldSpec)
        assert (spec.attr, spec.wire) == ('x', 'ex')
        assert spec.field is spec[2]

    def test_natural_init_replaces_field_defaults(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True)
            y: int | None = s.Int()
            z: int = s.Int(default=42)

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
            a: int | None = s.Int(data_key='propertyA')
            b: float | None = s.Float(data_key='propertyB')
            c: str | None = s.Str(data_key='propertyC')

        @s.seared
        class B(s.Seared):
            a: int = s.Int(default=5)
            b: float = s.Float(default=3.14)
            c: str = s.Str(default='hello')
            d: A = s.T(A, required=True)
            e: Color = s.Enum(enum=Color, default=Color.GREEN)
            f: list = s.Int(many=True, default=[])
            g: dict = s.Float(keyed=True, default={})

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
            tag: str = s.Str(required=True)

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
# Mutable ``default`` values — deep-copied per instance (was
# tests/test_mutable_defaults.py).
# ---------------------------------------------------------------------------


class TestListDefault:
    def test_two_instances_have_distinct_lists(self):
        @s.seared
        class Bag(s.Seared):
            tags: list = s.Str(many=True, default=[])

        a = Bag()
        b = Bag()
        a.tags.append('one')
        # Pre-fix: b.tags would also contain 'one' (same list object).
        assert b.tags == [], 'mutable-default fix regressed — instances are sharing the list'
        assert a.tags == ['one']

    def test_explicit_value_unaffected(self):
        @s.seared
        class Bag(s.Seared):
            tags: list = s.Str(many=True, default=[])

        explicit = ['a', 'b']
        a = Bag(tags=explicit)
        # Mutating the original list passed in changes a.tags (we don't
        # copy explicit user values; only missing-defaults).
        explicit.append('c')
        assert a.tags == ['a', 'b', 'c']  # documented passthrough


class TestDictDefault:
    def test_two_instances_have_distinct_dicts(self):
        @s.seared
        class Doc(s.Seared):
            meta: dict = s.Str(keyed=True, default={})

        a = Doc()
        b = Doc()
        a.meta['key'] = 'value'
        assert b.meta == {}, 'dict missing-default sharing regressed'

    def test_nested_mutable_isolated_via_deepcopy(self):
        """Pin deepcopy semantics: ``default={'tags': ['default']}``
        gives each instance its own OUTER dict AND its own INNER list.
        With shallow copy, the inner list would be shared."""

        @s.seared
        class Doc(s.Seared):
            meta: dict = s.Dict(default={'tags': ['default']})

        a = Doc()
        b = Doc()
        a.meta['tags'].append('shared?')
        assert b.meta == {'tags': ['default']}, (
            'nested mutable inside missing-default got shared — deepcopy failed to isolate the inner list'
        )


class TestSetDefault:
    def test_two_instances_have_distinct_sets(self):
        # No ``Set`` field type in seared; use ``Str(many=True)`` plus
        # a ``set`` default — the decorator's wrapper deepcopies the
        # raw default object regardless of the field's wire shape.
        @s.seared
        class Tags(s.Seared):
            members: set = s.Str(many=True, default=set())

        a = Tags()
        b = Tags()
        a.members.add('alpha')
        assert b.members == set()


class TestFrozensetDefault:
    def test_frozenset_default_deep_copied(self):
        @s.seared
        class Tags(s.Seared):
            members: frozenset = s.Str(many=True, default=frozenset())

        a = Tags()
        b = Tags()
        # Frozenset is immutable; both should be empty, equal.
        assert a.members == b.members == frozenset()


class TestImmutableDefault:
    def test_string_default_passthrough(self):
        @s.seared
        class Doc(s.Seared):
            tag: str = s.Str(default='default')

        a = Doc()
        b = Doc()
        # Strings are immutable; both share the same object — fine.
        assert a.tag == b.tag == 'default'

    def test_int_default_passthrough(self):
        @s.seared
        class Counter(s.Seared):
            n: int = s.Int(default=0)

        a = Counter()
        b = Counter()
        assert a.n == b.n == 0

    def test_none_default_passthrough(self):
        @s.seared
        class Maybe(s.Seared):
            value: object = s.Str(default=None)

        a = Maybe()
        assert a.value is None


# ---------------------------------------------------------------------------
# ``__post_init__`` sees resolved defaults — the dataclass ``__init__`` calls
# the hook before the ``__init__`` wrapper runs, so the decorator wraps the
# hook to substitute first.
# ---------------------------------------------------------------------------


def _recording():
    """A seared class whose hook records what it saw, and the record."""
    seen: list[dict[str, object]] = []

    @s.seared
    class Recorded(s.Seared):
        name: str | None = s.Str(default=None)
        count: int = s.Int(default=3)
        tags: list[str] = s.Str(many=True, default_factory=list)

        def __post_init__(self):
            seen.append({'name': self.name, 'count': self.count, 'tags': self.tags})

    return Recorded, seen


class TestPostInitSeesDefaults:
    def test_an_omitted_field_reads_as_its_default_in_the_hook(self):
        recorded, seen = _recording()

        recorded()

        assert seen == [{'name': None, 'count': 3, 'tags': []}]

    @pytest.mark.parametrize('build', ['construct', 'load'])
    def test_construction_and_load_hand_the_hook_the_same_values(self, build):
        # ``load`` always resolved omitted fields before constructing; natural
        # construction used to hand the hook the ``Field`` objects instead.
        recorded, seen = _recording()

        recorded() if build == 'construct' else recorded.load({})

        assert seen == [{'name': None, 'count': 3, 'tags': []}]

    def test_a_hook_can_refuse_an_omitted_field(self):
        @s.seared
        class Paired(s.Seared):
            layer: str = s.Str(default='')
            zone: int = s.Int(default=0)

            def __post_init__(self):
                if bool(self.layer) != bool(self.zone):
                    msg = 'layer and zone come together'
                    raise s.ValidationError(msg)

        Paired()
        Paired(layer='department', zone=4)
        with pytest.raises(s.ValidationError, match='come together'):
            Paired(layer='department')
        with pytest.raises(s.ValidationError, match='come together'):
            Paired.load({'zone': 4})

    def test_a_value_the_hook_assigns_is_kept(self):
        @s.seared
        class Derived(s.Seared):
            first: str = s.Str(required=True)
            label: str | None = s.Str(default=None)

            def __post_init__(self):
                if self.label is None:
                    self.label = self.first.upper()

        assert Derived(first='ab').label == 'AB'
        assert Derived(first='ab', label='given').label == 'given'

    def test_each_instance_gets_its_own_mutable_default_in_the_hook(self):
        @s.seared
        class Bag(s.Seared):
            tags: list[str] = s.Str(many=True, default_factory=list)

            def __post_init__(self):
                self.tags.append('seeded')

        a, b = Bag(), Bag()

        assert a.tags == ['seeded']
        assert b.tags == ['seeded']

    def test_an_inherited_hook_sees_the_subclass_fields_resolved(self):
        seen: list[object] = []

        @s.seared
        class Base(s.Seared):
            a: int = s.Int(default=1)

            def __post_init__(self):
                seen.append(getattr(self, 'b', 'absent'))

        @s.seared
        class Child(Base):
            b: str | None = s.Str(default=None)

        Child()

        assert seen == [None]

    def test_initvars_reach_the_hook(self):
        @s.seared
        class Scaled(s.Seared):
            value: int = s.Int(default=2)
            factor: InitVar[int] = 1

            def __post_init__(self, factor):
                self.value *= factor

        assert Scaled(factor=5).value == 10
        assert Scaled().value == 2


# ---------------------------------------------------------------------------
# Multi-Union fields — disjoint-key validation in ``_build`` (was
# tests/test_multi_union.py).
# ---------------------------------------------------------------------------


@s.seared
class _Up(s.Seared):
    speed: int = s.Int(required=True)


@s.seared
class _Down(s.Seared):
    reason: str = s.Str(default='')


@s.seared
class _Read(s.Seared):
    keys: list = s.Str(many=True, default=[])


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
                    variants={'up': _Up},
                    tag_key='type',
                )
                b: object = s.Union(
                    variants={'read': _Read},
                    tag_key='type',  # collision
                )

    def test_tag_payload_key_collision(self):
        """A's tag_key collides with B's payload_key — also rejected."""
        with pytest.raises(TypeError, match='share wire key'):

            @s.seared
            class Bad(s.Seared):
                a: object = s.Union(
                    variants={'up': _Up},
                    tag_key='kind',
                )
                b: object = s.Union(
                    variants={'read': _Read},
                    tag_key='b_type',
                    payload_key='kind',  # collision
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
    chunks: list = s.Bytes(many=True, default=[])


class TestJSONDefault:
    def test_default_serializes_to_base64_string(self):
        b = _Blob(payload=b'hello')
        d = _Blob.dump(b)
        assert d == {'payload': 'aGVsbG8='}  # base64 of 'hello'
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
        original = bytes(range(256))  # all byte values
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


# ---------------------------------------------------------------------------
# The per-object paths import nothing
# ---------------------------------------------------------------------------


@s.seared(accel=False)
class _Leaf(s.Seared):
    x: int = s.Int(required=True)
    tags: list[str] = s.Str(many=True, default_factory=list)


@s.seared(accel=False)
class _Hooked(s.Seared):
    x: int = s.Int(required=True)
    note: str = s.Str(default='')

    def __post_init__(self) -> None:
        """Exist, so construction takes the wrapped ``__post_init__`` path too."""


@s.seared(accel=False)
class _Tree(s.Seared):
    leaves: list[_Leaf] = s.T(_Leaf, many=True, required=True)
    hooked: _Hooked | None = s.T(_Hooked, default=None)
    tags: list[str] = s.Str(many=True, default_factory=list)


class TestPerObjectPathsImportNothing:
    """Pin: ``load``, construction and ``dump`` run no ``import`` statement.

    Each runs once per object, nested ones included, so an import inside them
    is paid on every call even when the module is cached. Two such imports in
    the default-filling path took about 11% off the pure-Python ``load`` of
    the benchmark schema, and no test noticed; this one would.
    """

    def test_no_import_runs(self, monkeypatch):
        imported: list[str] = []
        real_import = builtins.__import__

        def recording_import(name, *args, **kwargs):
            imported.append(name)
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', recording_import)

        tree = _Tree.load({'leaves': [{'x': 1}, {'x': 2, 'tags': ['a']}], 'hooked': {'x': 3}})
        _Tree(leaves=[_Leaf(x=4)], hooked=_Hooked(x=5))
        _Tree.dump(tree)

        assert imported == []


@s.seared(accel=False)
class _Enveloped(s.Seared):
    leaf: _Leaf = s.T(_Leaf, required=True)
    action: object = s.Union(variants={'leaf': _Leaf}, tag_key='kind', payload_key='args')


class TestUnwrapIsResolvedOnce:
    """Pin: ``load`` and ``dump`` never ask whether a field is ``UNWRAP``.

    The answer is fixed when the class is decorated. Asked per field per call,
    it cost about a tenth of the pure-Python ``load``.
    """

    def test_no_call_per_load_or_dump(self, monkeypatch):
        from seared._core import decorator

        calls: list[object] = []
        real = decorator._is_unwrap

        def counting(f):
            calls.append(f)
            return real(f)

        monkeypatch.setattr(decorator, '_is_unwrap', counting)

        tree = _Tree.load({'leaves': [{'x': 1}], 'hooked': {'x': 3}})
        _Tree.dump(tree)
        wire = {'leaf': {'x': 1, 'tags': []}, 'kind': 'leaf', 'args': {'x': 2, 'tags': []}}
        assert _Enveloped.dump(_Enveloped.load(wire)) == wire

        assert calls == []

    def test_a_class_decorated_later_still_resolves_it(self, monkeypatch):
        from seared._core import decorator

        calls: list[object] = []
        real = decorator._is_unwrap
        monkeypatch.setattr(decorator, '_is_unwrap', lambda f: calls.append(f) or real(f))

        @s.seared(accel=False)
        class Late(s.Seared):
            x: int = s.Int(required=True)
            action: object = s.Union(variants={'leaf': _Leaf}, tag_key='kind', payload_key='args')

        at_decoration = len(calls)
        Late.dump(Late.load({'x': 1, 'kind': 'leaf', 'args': {'x': 2}}))
        assert at_decoration > 0
        assert len(calls) == at_decoration


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


@s.seared
class _PathLeaf(s.Seared):
    n: int = s.Int(required=True)


@s.seared
class _PathPort(s.Seared):
    port: int = s.Int(required=True, data_key='p')


@s.seared
class _PathRoot(s.Seared):
    items: list[_PathLeaf] = s.T(_PathLeaf, many=True, required=True)
    readers: dict = s.T(_PathPort, keyed=True, default_factory=dict)


def _failure(fn, *args) -> s.ValidationError:
    with pytest.raises(s.ValidationError) as info:
        fn(*args)
    return info.value


class TestErrorPaths:
    """Pin: an error says where it happened, as a path into what the caller passed."""

    def test_a_load_path_retrieves_the_offending_value(self):
        data = {'items': [{'n': 1}, {'n': 2}, {'n': 'x'}]}
        e = _failure(_PathRoot.load, data)
        assert str(e) == "_PathRoot.items[2].n: cannot deserialize 'x' as int"
        assert functools.reduce(operator.getitem, e.path, data) == 'x'

    def test_keyed_keys_render_in_brackets_unless_identifiers(self):
        data = {'items': [], 'readers': {'r-1': {'p': 'bad'}}}
        e = _failure(_PathRoot.load, data)
        assert str(e) == "_PathRoot.readers['r-1'].p: cannot deserialize 'bad' as int"
        assert functools.reduce(operator.getitem, e.path, data) == 'bad'

    def test_a_missing_required_key_ends_the_path_at_the_absent_key(self):
        e = _failure(_PathRoot.load, {'items': [{}]})
        assert str(e) == '_PathRoot.items[0].n: required key missing'
        assert e.reason == 'required key missing'

    def test_a_required_key_is_named_by_its_wire_key(self):
        e = _failure(_PathPort.load, {})
        assert (e.path, str(e)) == (('p',), '_PathPort.p: required key missing')

    def test_a_non_dict_names_the_class_alone(self):
        e = _failure(_PathRoot.load, [])
        assert (str(e), e.path) == ('_PathRoot: expected dict, got list', ())

    def test_a_dump_path_names_attributes(self):
        obj = _PathRoot(items=[], readers={'r-1': _PathPort(port='bad')})
        e = _failure(_PathRoot.dump, obj)
        assert e.path == ('readers', 'r-1', 'port')
        assert str(e) == "_PathRoot.readers['r-1'].port: expected int, got str"

    def test_a_post_init_validation_error_names_the_object(self):
        @s.seared
        class Window(s.Seared):
            lo: int = s.Int(required=True)
            hi: int = s.Int(required=True)

            def __post_init__(self):
                if self.hi < self.lo:
                    msg = 'window ends before it starts'
                    raise s.ValidationError(msg)

        @s.seared
        class Plan(s.Seared):
            windows: list[Window] = s.T(Window, many=True, required=True)

        assert str(_failure(Window.load, {'lo': 5, 'hi': 1})) == 'Window: window ends before it starts'
        e = _failure(Plan.load, {'windows': [{'lo': 1, 'hi': 2}, {'lo': 5, 'hi': 1}]})
        assert str(e) == 'Plan.windows[1]: window ends before it starts'

    def test_other_exceptions_pass_through_untouched(self):
        @s.seared
        class Picky(s.Seared):
            v: int = s.Int(required=True)

            def __post_init__(self):
                msg = 'not a seared error'
                raise ValueError(msg)

        with pytest.raises(ValueError, match=r'^not a seared error$') as info:
            Picky.load({'v': 1})
        assert not isinstance(info.value, s.ValidationError)

    def test_a_field_raising_on_its_own_stays_bare(self):
        e = _failure(s.Int().deserialize, 'x')
        assert (str(e), e.path, e.cls_name) == ("cannot deserialize 'x' as int", (), None)


# ---------------------------------------------------------------------------
# Null on the wire — a ``null`` is a value only on a ``nullable`` field.
# ---------------------------------------------------------------------------


def _null_table(validate=True):
    """One field per column of the null table: a required field, a defaulted one, and so on."""

    @s.seared(validate=validate)
    class Row(s.Seared):
        req: int = s.Int(required=True)
        dflt: int = s.Int(default=5)
        bare: int | None = s.Int()
        n_dflt: int | None = s.Int(nullable=True, default=5)
        n_req: int | None = s.Int(nullable=True, required=True)

    return Row


#: The wire states, each turned into a payload for one column: absent, ``null`` or a value.
_ABSENT, _NULL = object(), None
_BASE = {'req': 1, 'n_req': 2}
_ERROR = 'required key missing'

#: (column, absent, null, value) — what ``load`` gives for each wire state.
_TABLE = [
    ('req', _ERROR, _ERROR, 7),
    ('dflt', 5, 5, 7),
    ('bare', None, None, 7),
    ('n_dflt', 5, None, 7),
    ('n_req', _ERROR, None, 7),
]


def _loaded(cls, column, wire):
    data = {k: v for k, v in _BASE.items() if k != column}
    if wire is not _ABSENT:
        data[column] = wire
    try:
        return getattr(cls.load(data), column)
    except s.ValidationError as e:
        return e.reason


class TestNullOnTheWire:
    """Pin: a ``null`` on a field that isn't nullable reads as an absent key."""

    @pytest.mark.parametrize('validate', [True, False], ids=['strict', 'lax'])
    @pytest.mark.parametrize(('column', 'absent', 'null', 'value'), _TABLE, ids=[r[0] for r in _TABLE])
    def test_the_null_table(self, validate, column, absent, null, value):
        cls = _null_table(validate)
        assert _loaded(cls, column, _ABSENT) == absent
        assert _loaded(cls, column, _NULL) == null
        assert _loaded(cls, column, 7) == value

    def test_a_null_on_a_required_field_names_its_wire_key(self):
        @s.seared
        class Port(s.Seared):
            port: int = s.Int(required=True, data_key='p')

        e = _failure(Port.load, {'p': None})
        assert (str(e), e.path) == ('Port.p: required key missing', ('p',))

    def test_a_null_takes_the_default_factory(self):
        @s.seared
        class Tagged(s.Seared):
            tags: list[str] = s.Str(many=True, default_factory=list)

        assert Tagged.load({'tags': None}).tags == []

    def test_a_null_nested_object_is_absent(self):
        e = _failure(_PathRoot.load, {'items': None})
        assert str(e) == '_PathRoot.items: required key missing'
        assert _PathRoot.load({'items': [], 'readers': None}).readers == {}

    def test_a_null_inside_a_nested_object_follows_its_own_field(self):
        e = _failure(_PathRoot.load, {'items': [{'n': None}]})
        assert str(e) == '_PathRoot.items[0].n: required key missing'

    def test_a_nullable_collection_can_be_null(self):
        @s.seared
        class Readings(s.Seared):
            values: list[int] | None = s.Int(many=True, nullable=True, default_factory=list)
            named: dict[str, int] | None = s.Int(keyed=True, nullable=True)

        got = Readings.load({'values': None, 'named': None})
        assert (got.values, got.named) == (None, None)
        assert Readings.load({}).values == []

    def test_a_null_element_is_still_an_error(self):
        @s.seared
        class Readings(s.Seared):
            values: list[int] | None = s.Int(many=True, nullable=True)

        e = _failure(Readings.load, {'values': [1, None]})
        assert e.path == ('values', 1)

    def test_a_nullable_nested_object_can_be_null(self):
        @s.seared
        class Holder(s.Seared):
            port: _PathPort | None = s.T(_PathPort, nullable=True, required=True)

        assert Holder.load({'port': None}).port is None
        assert str(_failure(Holder.load, {})) == 'Holder.port: required key missing'


class TestNullOnDump:
    """Pin: ``dump`` writes ``null`` only for a nullable field; ``load`` reads either back the same."""

    def test_only_a_nullable_none_is_written(self):
        cls = _null_table()
        row = cls(req=1, n_req=None, n_dflt=None)
        assert cls.dump(row) == {'req': 1, 'dflt': 5, 'n_dflt': None, 'n_req': None}

    def test_a_nullable_none_survives_a_round_trip_over_its_default(self):
        cls = _null_table()
        row = cls(req=1, n_req=None, n_dflt=None)
        back = cls.load(json.loads(json.dumps(cls.dump(row))))
        assert back == row

    def test_a_non_nullable_none_round_trips_as_its_default(self):
        cls = _null_table()
        row = cls(req=1, n_req=2, dflt=None)
        assert 'dflt' not in cls.dump(row)
        assert cls.load(cls.dump(row)).dflt == 5

    def test_dump_false_wins_over_nullable(self):
        @s.seared
        class Hidden(s.Seared):
            secret: str | None = s.Str(nullable=True, dump=False)

        assert Hidden.dump(Hidden()) == {}


@s.seared
class _Lenient(s.Seared):
    n: int = s.Int(default=0)
    must: str = s.Str(default='')


@s.seared(unknown='raise')
class _Strict(s.Seared):
    n: int = s.Int(default=0)
    must: str | None = s.Str(default=None)


@s.seared(unknown='raise')
class _StrictRequired(s.Seared):
    retention: str = s.Str(required=True)


class TestUnknownOption:
    """``@seared(unknown=…)`` and ``load(unknown=…)`` (0.4.1)."""

    def test_by_default_an_unknown_key_is_dropped(self):
        assert _Lenient.load({'n': 2, 'nn': 3}) == _Lenient(n=2)
        assert _Lenient.__seared_unknown__ == 'ignore'

    def test_a_refusing_class_raises_at_the_unknown_key(self):
        with pytest.raises(s.ValidationError, match=r'^_Strict\.nn: unknown key$'):
            _Strict.load({'n': 2, 'nn': 3})
        assert _Strict.__seared_unknown__ == 'raise'

    def test_a_refusing_class_still_loads_known_keys(self):
        assert _Strict.load({'n': 2, 'must': 'x'}) == _Strict(n=2, must='x')

    def test_a_call_can_refuse_for_a_lenient_class(self):
        with pytest.raises(s.ValidationError, match='unknown key'):
            _Lenient.load({'nn': 3}, unknown='raise')

    def test_a_call_can_ignore_for_a_refusing_class(self):
        assert _Strict.load({'n': 2, 'nn': 3}, unknown='ignore') == _Strict(n=2)

    def test_unknown_is_also_the_third_positional_argument(self):
        with pytest.raises(s.ValidationError, match='unknown key'):
            _Lenient.load({'nn': 3}, 'json', 'raise')

    def test_the_refusal_runs_before_the_load(self):
        # A misspelt required key: the unknown key says why, where "required key
        # missing" would only say what.
        with pytest.raises(s.ValidationError, match=r'^_StrictRequired\.retension: unknown key$'):
            _StrictRequired.load({'retension': '7d'})

    def test_data_that_isnt_a_dict_keeps_its_own_error(self):
        with pytest.raises(s.ValidationError, match='expected dict'):
            _Strict.load(['n'])

    def test_a_bad_option_is_refused_at_decoration(self):
        with pytest.raises(ValueError, match="@seared: unknown= takes 'ignore' or 'raise', got 'strict'"):

            @s.seared(unknown='strict')  # ty: ignore[invalid-argument-type]
            class _Bad(s.Seared):
                n: int = s.Int(default=0)

    @pytest.mark.parametrize('cls', [_Lenient, _Strict])
    def test_a_bad_option_is_refused_per_call(self, cls):
        with pytest.raises(ValueError, match=rf"{cls.__name__}\.load: unknown= takes 'ignore' or 'raise'"):
            cls.load({'n': 1}, unknown='strict')  # ty: ignore[invalid-argument-type]

    def test_loads_takes_the_option_too(self):
        assert _Lenient.loads('{"n": 2, "nn": 3}') == _Lenient(n=2)
        with pytest.raises(s.ValidationError, match='unknown key'):
            _Lenient.loads('{"n": 2, "nn": 3}', unknown='raise')
        with pytest.raises(s.ValidationError, match='unknown key'):
            _Strict.loads('{"n": 2, "nn": 3}')

    def test_the_bare_load_sits_behind_the_option(self):
        # What a nested ``T`` or ``Union`` calls: the class's own load, no option in front.
        assert _Strict.__seared_load__({'n': 2, 'nn': 3}, 'json') == _Strict(n=2)
