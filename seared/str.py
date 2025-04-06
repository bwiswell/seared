from dataclasses import dataclass
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Field as MField, String

from .field import Field


@dataclass(frozen=True)
class StrMeta:
    missing: Optional[str] = None


@dataclass(frozen=True)
class Str(Field, StrMeta):

    def to_field (self, name: str) -> MField:
        return self.wrap(
            String,
            data_key = self.data_key if self.data_key else name,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )