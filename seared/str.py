from dataclasses import dataclass
from typing import Optional

from marshmallow.fields import Field, String

from .field import Field


@dataclass(frozen=True)
class Str(Field):
    missing: Optional[str] = None
    keyed: bool = False
    many: bool = False

    def to_field (self, _: str) -> Field:
        return self.wrap(
            String,
            self.keyed,
            self.many,
            data_key = self.data_key,
            missing = self.missing
        )