from dataclasses import dataclass
from enum import Enum as PEnum
from typing import Optional, TypeVar, Union

from marshmallow.fields import Field, Function

from .field import Field


ET = TypeVar('ET', bound=PEnum)


@dataclass(frozen=True)
class Enum(Field):
    enum: ET = None
    missing: Optional[ET] = None
    keyed: bool = False
    many: bool = False

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
            self.keyed,
            self.many,
            data_key = self.data_key,
            missing = self.missing
        )