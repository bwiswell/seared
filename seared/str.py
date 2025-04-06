from dataclasses import dataclass
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Field, String

from .field import Field, FieldMeta


@dataclass(frozen=True)
class StrMeta(Field):
    missing: Optional[str] = None


@dataclass(frozen=True)
class Str(FieldMeta, StrMeta):

    def to_field (self, _: str) -> Field:
        return self.wrap(
            String,
            data_key = self.data_key,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )