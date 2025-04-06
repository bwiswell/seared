from dataclasses import dataclass
from typing import Any, Optional, TypeVar

from marshmallow import Schema
from marshmallow.fields import Field, Function

from .field import Field


TT = TypeVar('TT', bound=object)


@dataclass(frozen=True)
class T(Field):
    schema: Schema = None
    missing: Optional[TT] = None
    keyed: bool = False
    many: bool = False

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
            self.keyed,
            self.many,
            data_key=self.data_key,
            missing=self.missing
        )