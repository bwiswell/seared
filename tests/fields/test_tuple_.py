from __future__ import annotations

import pytest

import seared as s


class TestTuple:
    def test_load(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple = s.Tuple(s.Float(), s.Float(), required=True)

        obj = Obj.load({'point': [1.0, 2.0]})
        assert obj.point == (1.0, 2.0)

    def test_dump(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple = s.Tuple(s.Float(), s.Float(), required=True)

        d = Obj.dump(Obj(point=(1.0, 2.0)))
        # Tuple serialises to a Python tuple; JSON output is a list
        assert d['point'] == (1.0, 2.0)

    def test_json_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple = s.Tuple(s.Float(), s.Float(), required=True)

        obj = Obj.loads(Obj.dumps(Obj(point=(3.14, 2.72))))
        assert obj.point == (3.14, 2.72)

    def test_mixed_types(self):
        @s.seared
        class Obj(s.Seared):
            record: tuple = s.Tuple(s.Str(), s.Int(), s.Bool(), required=True)

        obj = Obj.load({'record': ['alice', 42, True]})
        assert obj.record == ('alice', 42, True)
        assert Obj.dump(obj)['record'] == ('alice', 42, True)

    def test_single_element(self):
        @s.seared
        class Obj(s.Seared):
            wrap: tuple = s.Tuple(s.Int(), required=True)

        obj = Obj.load({'wrap': [7]})
        assert obj.wrap == (7,)
        assert Obj.dump(obj)['wrap'] == (7,)

    def test_optional_none_excluded_from_dump(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple | None = s.Tuple(s.Float(), s.Float())

        d = Obj.dump(Obj(point=None))
        assert 'point' not in d

    def test_nullable_passes_through(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple | None = s.Tuple(s.Float(), s.Float(), nullable=True, default=(0.0, 0.0))

        assert Obj.__seared_fields__[0].field.nullable is True
        assert Obj.load({'point': None}).point is None
        assert Obj.load({}).point == (0.0, 0.0)
        assert Obj.dump(Obj(point=None)) == {'point': None}

    def test_default(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple = s.Tuple(s.Float(), s.Float(), default=(0.0, 0.0))

        obj = Obj.load({})
        assert obj.point == (0.0, 0.0)

    def test_many_load(self):
        @s.seared
        class Obj(s.Seared):
            points: list = s.Tuple(s.Float(), s.Float(), many=True, required=True)

        obj = Obj.load({'points': [[1.0, 2.0], [3.0, 4.0]]})
        assert obj.points == [(1.0, 2.0), (3.0, 4.0)]

    def test_many_json_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            points: list = s.Tuple(s.Float(), s.Float(), many=True, required=True)

        obj = Obj.loads(Obj.dumps(Obj(points=[(1.0, 2.0), (3.0, 4.0)])))
        assert obj.points == [(1.0, 2.0), (3.0, 4.0)]

    def test_data_key(self):
        @s.seared
        class Obj(s.Seared):
            point: tuple = s.Tuple(s.Float(), s.Float(), data_key='coords', required=True)

        obj = Obj.load({'coords': [5.0, 6.0]})
        assert obj.point == (5.0, 6.0)
        d = Obj.dump(obj)
        assert 'coords' in d
        assert 'point' not in d


class TestErrorPaths:
    """Pin: a failing slot adds its index to the path."""

    def test_a_slot_error_on_its_own(self):
        with pytest.raises(s.ValidationError) as info:
            s.Tuple(s.Int(), s.Str()).deserialize([1, 2])
        assert (info.value.path, str(info.value)) == ((1,), '[1]: expected str, got int')

    def test_a_slot_error_inside_a_class(self):
        @s.seared
        class Obj(s.Seared):
            pair: tuple = s.Tuple(s.Int(), s.Str(), required=True)

        with pytest.raises(s.ValidationError) as info:
            Obj.load({'pair': ['x', 'y']})
        assert str(info.value) == "Obj.pair[0]: cannot deserialize 'x' as int"


@s.seared
class _Blob(s.Seared):
    data: bytes = s.Bytes(required=True)


@s.seared
class _Pairs(s.Seared):
    pair: tuple = s.Tuple(s.Bytes(), s.Int(), required=True)
    nested: tuple | None = s.Tuple(s.T(_Blob), s.Str(), default=None)
    many: list = s.Tuple(s.Bytes(), s.Int(), many=True, default_factory=list)


class TestFormatHint:
    """Pin: ``format=`` reaches every slot, as it crosses into a ``T``.

    Until 0.4.0 the slots were called without it, so a ``Bytes`` slot stayed
    base64 under ``format='msgpack'`` while a top-level ``Bytes`` went native.
    """

    def test_dump_threads_msgpack_into_the_slots(self):
        obj = _Pairs(pair=(b'\x00\x01', 2), nested=(_Blob(data=b'\x02'), 'x'), many=[(b'\x03', 4)])
        assert _Pairs.dump(obj, format='msgpack') == {
            'pair': (b'\x00\x01', 2),
            'nested': ({'data': b'\x02'}, 'x'),
            'many': [(b'\x03', 4)],
        }

    def test_dump_default_is_still_json(self):
        obj = _Pairs(pair=(b'\x00\x01', 2), nested=(_Blob(data=b'\x02'), 'x'))
        assert _Pairs.dump(obj) == {'pair': ('AAE=', 2), 'nested': ({'data': 'Ag=='}, 'x'), 'many': []}

    def test_load_reads_raw_bytes_under_msgpack(self):
        raw = {'pair': [b'\x00\x01', 2], 'nested': [{'data': b'\x02'}, 'x']}
        obj = _Pairs.load(raw, format='msgpack')
        assert (obj.pair, obj.nested[0].data) == ((b'\x00\x01', 2), b'\x02')

    def test_a_payload_written_before_the_fix_still_loads(self):
        # It carried base64 in the slot even under msgpack, and ``Bytes``
        # reads either form under any carrier.
        obj = _Pairs.load({'pair': ['AAE=', 2]}, format='msgpack')
        assert obj.pair == (b'\x00\x01', 2)

    def test_direct_field_call_defaults_to_json(self):
        field = s.Tuple(s.Bytes(), s.Int())
        assert field.serialize((b'\x00\x01', 2)) == ('AAE=', 2)
        assert field.deserialize(['AAE=', 2]) == (b'\x00\x01', 2)
