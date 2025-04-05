from dataclasses import dataclass
from enum import Enum as PEnum
from typing import Optional, TypeVar, Union

from marshmallow.fields import Field, Function

from .field import Field


ET = TypeVar('ET', PEnum, PEnum)


@dataclass
class Enum(Field):
    enum: ET
    missing: Optional[ET] = None

    def to_field (self, name: str) -> Field:
        def deserialize (value: Union[int, str]) -> ET:
            return self.enum(int(value))
        def serialize (cls: object) -> Optional[int]:
            value = cls.__getattribute__(name)
            if value is None: return None
            return value.value
        return Function(
            serialize = serialize,
            deserialize = deserialize,
            data_key = self.data_key,
            missing = self.missing
        )