import base64
from dataclasses import dataclass
from typing import Literal, Optional

from marshmallow import missing
from marshmallow.fields import Field as MField

from .field import Field


@dataclass(frozen=True)
class BytesMeta:
    encoding: Literal['base64', 'hex'] = 'base64'
    missing: Optional[bytes] = None


@dataclass(frozen=True)
class Bytes(Field, BytesMeta):

    def to_field(self, name: str) -> MField:
        encoding = self.encoding

        class BytesField(MField):
            def _serialize(self, value, attr, obj, **kwargs):
                if value is None:
                    return None
                if encoding == 'hex':
                    return value.hex()
                return base64.b64encode(value).decode('ascii')

            def _deserialize(self, value, attr, data, **kwargs):
                if encoding == 'hex':
                    return bytes.fromhex(value)
                return base64.b64decode(value)

        return self.wrap(
            BytesField,
            data_key=self.data_key if self.data_key else name,
            load_only=not self.dump,
            load_default=self._load_default(missing)
        )
