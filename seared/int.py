from dataclasses import dataclass
from typing import Optional

from marshmallow.fields import Field, Integer

from .field import Field


@dataclass(frozen=True)
class Int(Field):
    missing: Optional[int] = None

    def to_field (self, _: str) -> Field:
        return Integer(
            data_key = self.data_key,
            missing = self.missing
        )