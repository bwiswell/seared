from dataclasses import dataclass
from typing import Optional

from marshmallow.fields import Field, Float as MFloat

from .field import Field


@dataclass(frozen=True)
class Float(Field):
    missing: Optional[float] = None
    keyed: bool = False
    many: bool = False

    def to_field (self, _: str) -> Field:
        return self.wrap(
            MFloat,
            self.keyed,
            self.many,
            data_key = self.data_key,
            missing = self.missing
        )