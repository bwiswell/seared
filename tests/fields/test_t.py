from __future__ import annotations

import seared as s


@s.seared
class Inner(s.Seared):
    x: int = s.Int(required=True)
    label: str | None = s.Str()


class TestT:
    def test_simple_load(self):
        @s.seared
        class Outer(s.Seared):
            inner: Inner = s.T(schema=Inner, required=True)

        obj = Outer.load({'inner': {'x': 5, 'label': 'hi'}})
        assert isinstance(obj.inner, Inner)
        assert obj.inner.x == 5
        assert obj.inner.label == 'hi'

    def test_simple_dump(self):
        @s.seared
        class Outer(s.Seared):
            inner: Inner = s.T(schema=Inner, required=True)

        obj = Outer(inner=Inner(x=5, label='hi'))
        d = Outer.dump(obj)
        assert d == {'inner': {'x': 5, 'label': 'hi'}}

    def test_simple_round_trip(self):
        @s.seared
        class Outer(s.Seared):
            inner: Inner = s.T(schema=Inner, required=True)

        raw = {'inner': {'x': 7}}
        obj = Outer.load(raw)
        assert Outer.dump(obj)['inner']['x'] == 7

    def test_optional_none_excluded_from_dump(self):
        @s.seared
        class Outer(s.Seared):
            inner: Inner | None = s.T(schema=Inner)

        d = Outer.dump(Outer(inner=None))
        assert 'inner' not in d

    def test_many_load(self):
        @s.seared
        class Outer(s.Seared):
            items: list = s.T(schema=Inner, many=True, required=True)

        obj = Outer.load({'items': [{'x': 1}, {'x': 2, 'label': 'b'}]})
        assert len(obj.items) == 2
        assert obj.items[0].x == 1
        assert obj.items[1].x == 2
        assert obj.items[1].label == 'b'

    def test_many_dump(self):
        @s.seared
        class Outer(s.Seared):
            items: list = s.T(schema=Inner, many=True, required=True)

        obj = Outer(items=[Inner(x=1, label=None), Inner(x=2, label='b')])
        d = Outer.dump(obj)
        assert d['items'][0] == {'x': 1}
        assert d['items'][1] == {'x': 2, 'label': 'b'}

    def test_many_round_trip(self):
        @s.seared
        class Outer(s.Seared):
            items: list = s.T(schema=Inner, many=True, required=True)

        raw = {'items': [{'x': 3}, {'x': 4, 'label': 'four'}]}
        obj = Outer.load(raw)
        d = Outer.dump(obj)
        assert d['items'][0] == {'x': 3}
        assert d['items'][1] == {'x': 4, 'label': 'four'}

    def test_keyed_load(self):
        @s.seared
        class Outer(s.Seared):
            mapping: dict = s.T(schema=Inner, keyed=True, required=True)

        obj = Outer.load({'mapping': {'a': {'x': 10}, 'b': {'x': 20, 'label': 'b'}}})
        assert obj.mapping['a'].x == 10
        assert obj.mapping['b'].x == 20

    def test_keyed_dump(self):
        @s.seared
        class Outer(s.Seared):
            mapping: dict = s.T(schema=Inner, keyed=True, required=True)

        obj = Outer(mapping={'a': Inner(x=10, label=None), 'b': Inner(x=20, label='b')})
        d = Outer.dump(obj)
        assert d['mapping']['a'] == {'x': 10}
        assert d['mapping']['b'] == {'x': 20, 'label': 'b'}

    def test_keyed_round_trip(self):
        @s.seared
        class Outer(s.Seared):
            mapping: dict = s.T(schema=Inner, keyed=True, required=True)

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
            inner: Inner = s.T(schema=Inner, data_key='nested', required=True)

        obj = Outer.load({'nested': {'x': 99}})
        assert obj.inner.x == 99
        d = Outer.dump(obj)
        assert 'nested' in d
        assert 'inner' not in d


class TestFormatHint:
    """``format=`` must cross the nesting boundary.

    Before 0.3.1 ``T`` called ``schema.dump(value)`` / ``schema.load(value)``
    with no hint, so a nested ``Bytes`` fell back to base64 under
    ``format='msgpack'`` while a top-level one went native — and the compiled
    core, which threads the hint, observably diverged from the Python path.
    """

    @s.seared
    class Blob(s.Seared):
        data: bytes = s.Bytes(required=True)

    def _outer(self):
        Blob = self.Blob

        @s.seared
        class Outer(s.Seared):
            top: bytes = s.Bytes(required=True)
            one: Blob = s.T(Blob, required=True)
            many: list[Blob] = s.T(Blob, many=True, default_factory=list)
            keyed: dict[str, Blob] = s.T(Blob, keyed=True, default_factory=dict)

        return Outer

    def test_dump_threads_msgpack_into_nested(self):
        Outer = self._outer()
        obj = Outer(
            top=b'\x00',
            one=self.Blob(data=b'\x01'),
            many=[self.Blob(data=b'\x02')],
            keyed={'k': self.Blob(data=b'\x03')},
        )
        d = Outer.dump(obj, format='msgpack')
        assert d == {
            'top': b'\x00',
            'one': {'data': b'\x01'},
            'many': [{'data': b'\x02'}],
            'keyed': {'k': {'data': b'\x03'}},
        }

    def test_dump_default_is_still_json(self):
        Outer = self._outer()
        obj = Outer(top=b'\x00', one=self.Blob(data=b'\x01'))
        assert Outer.dump(obj) == {'top': 'AA==', 'one': {'data': 'AQ=='}, 'many': [], 'keyed': {}}

    def test_load_threads_msgpack_into_nested(self):
        Outer = self._outer()
        raw = {'top': b'\x00', 'one': {'data': b'\x01'}, 'many': [{'data': b'\x02'}]}
        obj = Outer.load(raw, format='msgpack')
        assert (obj.top, obj.one.data, obj.many[0].data) == (b'\x00', b'\x01', b'\x02')

    def test_direct_field_call_defaults_to_json(self):
        # ``T.serialize`` called outside the decorator, with no hint at all.
        field = s.T(self.Blob)
        assert field.serialize(self.Blob(data=b'\x01')) == {'data': 'AQ=='}
        assert field.deserialize({'data': 'AQ=='}).data == b'\x01'
