from dataclasses import dataclass
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Field, Integer

from .field import Field, FieldMeta


@dataclass(frozen=True)
class IntMeta(Field):
    missing: Optional[int] = None


@dataclass(frozen=True)
class Int(FieldMeta, IntMeta):

    def to_field (self, _: str) -> Field:
        return self.wrap(
            Integer,
            data_key = self.data_key,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )