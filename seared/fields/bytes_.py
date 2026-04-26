from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Literal

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Bytes(Field):
    encoding: Literal['base64', 'hex'] = 'base64'

    def serialize(self, value, validate: bool = True, **kwargs):
        if validate and not isinstance(value, (bytes, bytearray, memoryview)):
            raise ValidationError(f'expected bytes, got {type(value).__name__}')
        raw = bytes(value)
        # Native binary on the wire — only valid when the carrier codec
        # supports raw bytes (msgpack does; JSON doesn't). Saves the
        # ~33% base64 overhead.
        if kwargs.get('format') == 'msgpack':
            return raw
        if self.encoding == 'hex':
            return raw.hex()
        return base64.b64encode(raw).decode('ascii')

    def deserialize(self, value, validate: bool = True, **kwargs) -> bytes:
        # Native bytes path — accept directly when carrier was msgpack.
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        if validate and not isinstance(value, str):
            raise ValidationError(f'expected str for Bytes, got {type(value).__name__}')
        try:
            if self.encoding == 'hex':
                return bytes.fromhex(value)
            return base64.b64decode(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(f'invalid {self.encoding} bytes: {value!r}') from e
