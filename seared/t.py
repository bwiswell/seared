from dataclasses import dataclass
from typing import Any, Optional, TypeVar

from marshmallow import Schema, missing
from marshmallow.fields import Field, Function

from .field import Field, FieldMeta


TT = TypeVar('TT', bound=object)


@dataclass(frozen=True)
class TMeta(Field):
    schema: Schema
    missing: Optional[TT] = None


@dataclass(frozen=True)
class T(FieldMeta, TMeta):

    def to_field (self, name: str) -> Field:
        def deserialize (value: dict[str, Any]) -> TT:
            return self.schema.load(value)
        def serialize (cls: object) -> Optional[dict[str, Any]]:
            value = cls.__getattribute__(name)
            if value is None: return None
            return self.schema.dump(value)
        return self.wrap(
            lambda **kws: Function(
                serialize = serialize,
                deserialize = deserialize,
                **kws
            ),
            data_key=self.data_key,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )