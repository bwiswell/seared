from dataclasses import dataclass
from typing import Optional

from marshmallow.fields import Field, Integer

from .field import Field, FieldMeta


@dataclass(frozen=True)
class IntMeta(Field):
    missing: Optional[int] = None


@dataclass(frozen=True)
class Int(IntMeta, FieldMeta):

    def to_field (self, _: str) -> Field:
        return self.wrap(
            Integer,
            data_key = self.data_key,
            missing = self.missing
        )