from dataclasses import dataclass
from typing import Optional

from marshmallow.fields import Field, Integer

from .field import Field


@dataclass(frozen=True)
class Int(Field):
    missing: Optional[int] = None
    keyed: bool = False
    many: bool = False

    def to_field (self, _: str) -> Field:
        return self.wrap(
            Integer,
            self.keyed,
            self.many,
            data_key = self.data_key,
            missing = self.missing
        )