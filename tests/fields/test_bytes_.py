from __future__ import annotations

import base64
from typing import Optional

import seared as s


class TestBytes:
    def test_load_base64(self):
        @s.seared
        class Obj(s.Seared):
            data: bytes = s.Bytes(required=True)

        encoded = base64.b64encode(b'hello').decode('ascii')
        obj = Obj.load({'data': encoded})
        assert obj.data == b'hello'

    def test_dump_base64(self):
        @s.seared
        class Obj(s.Seared):
            data: bytes = s.Bytes(required=True)

        d = Obj.dump(Obj(data=b'hello'))
        assert d == {'data': base64.b64encode(b'hello').decode('ascii')}

    def test_round_trip_base64(self):
        @s.seared
        class Obj(s.Seared):
            data: bytes = s.Bytes(required=True)

        raw = {'data': base64.b64encode(b'\x00\xff\x80').decode('ascii')}
        obj = Obj.load(raw)
        assert Obj.dump(obj) == raw

    def test_load_hex(self):
        @s.seared
        class Obj(s.Seared):
            data: bytes = s.Bytes(encoding='hex', required=True)

        obj = Obj.load({'data': 'deadbeef'})
        assert obj.data == bytes.fromhex('deadbeef')

    def test_dump_hex(self):
        @s.seared
        class Obj(s.Seared):
            data: bytes = s.Bytes(encoding='hex', required=True)

        d = Obj.dump(Obj(data=b'\xde\xad\xbe\xef'))
        assert d == {'data': 'deadbeef'}

    def test_round_trip_hex(self):
        @s.seared
        class Obj(s.Seared):
            data: bytes = s.Bytes(encoding='hex', required=True)

        raw = {'data': 'cafebabe'}
        obj = Obj.load(raw)
        assert Obj.dump(obj) == raw

    def test_optional_none_excluded_from_dump(self):
        @s.seared
        class Obj(s.Seared):
            data: Optional[bytes] = s.Bytes()

        d = Obj.dump(Obj(data=None))
        assert 'data' not in d

    def test_missing_default(self):
        @s.seared
        class Obj(s.Seared):
            data: bytes = s.Bytes(missing=b'default')

        obj = Obj.load({})
        assert obj.data == b'default'

    def test_empty_bytes(self):
        @s.seared
        class Obj(s.Seared):
            data: bytes = s.Bytes(required=True)

        obj = Obj.load({'data': base64.b64encode(b'').decode('ascii')})
        assert obj.data == b''
        assert Obj.dump(obj) == {'data': ''}
