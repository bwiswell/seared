from dataclasses import dataclass
from enum import Enum as PEnum
from typing import Optional, TypeVar, Union

from marshmallow.fields import Field, Function

from .field import Field, FieldMeta


ET = TypeVar('ET', bound=PEnum)


@dataclass(frozen=True)
class EnumMeta(Field):
    enum: ET
    missing: Optional[ET] = None


@dataclass(frozen=True)
class Enum(FieldMeta, EnumMeta):

    def to_field (self, name: str) -> Field:
        def deserialize (value: Union[int, str]) -> ET:
            return self.enum(int(value))
        def serialize (cls: object) -> Optional[int]:
            value = cls.__getattribute__(name)
            if value is None: return None
            return value.value
        return self.wrap(
            lambda **kws: Function(
                serialize = serialize,
                deserialize = deserialize,
                **kws
            ),
            data_key = self.data_key,
            load_only = not self.write,
            missing = self.missing
        )