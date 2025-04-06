from dataclasses import dataclass
from typing import Optional

from marshmallow.fields import Field, Float as MFloat

from .field import Field


@dataclass(frozen=True)
class Float(Field):
    missing: Optional[float] = None

    def to_field (self, _: str) -> Field:
        return MFloat(
            data_key = self.data_key,
            missing = self.missing
        )