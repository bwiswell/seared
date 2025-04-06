from dataclasses import dataclass
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Field, Float as MFloat

from .field import Field, FieldMeta


@dataclass(frozen=True)
class FloatMeta(Field):
    missing: Optional[float] = None
    

@dataclass(frozen=True)
class Float(FieldMeta, FloatMeta):

    def to_field (self, _: str) -> Field:
        return self.wrap(
            MFloat,
            data_key = self.data_key,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )