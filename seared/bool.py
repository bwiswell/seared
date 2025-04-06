from dataclasses import dataclass
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Bool as MBool, Field as MField

from .field import Field


@dataclass(frozen=True)
class BoolMeta:
    missing: Optional[bool] = None


@dataclass(frozen=True)
class Bool(Field, BoolMeta):

    def to_field (self, name: str) -> MField:
        return self.wrap(
            MBool,
            data_key = self.data_key if self.data_key else name,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )