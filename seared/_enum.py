from dataclasses import dataclass
from enum import Enum as PEnum
from typing import Optional, TypeVar, Union

from marshmallow import missing
from marshmallow.fields import Field as MField, Function

from .field import Field


ET = TypeVar('ET', bound=PEnum)


@dataclass(frozen=True)
class EnumMeta:
    enum: ET
    missing: Optional[ET] = None


@dataclass(frozen=True)
class Enum(Field, EnumMeta):

    def to_field (self, name: str) -> MField:
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
            data_key = self.data_key if self.data_key else name,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )