from dataclasses import dataclass
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Field as MField, Integer

from .field import Field


@dataclass(frozen=True)
class IntMeta:
    missing: Optional[int] = None


@dataclass(frozen=True)
class Int(Field, IntMeta):

    def to_field (self, name: str) -> MField:
        return self.wrap(
            Integer,
            data_key = self.data_key if self.data_key else name,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )