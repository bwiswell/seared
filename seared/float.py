from dataclasses import dataclass
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Field as MField, Float as MFloat

from .field import Field


@dataclass(frozen=True)
class FloatMeta:
    missing: Optional[float] = None
    

@dataclass(frozen=True)
class Float(Field, FloatMeta):

    def to_field (self, name: str) -> MField:
        return self.wrap(
            MFloat,
            data_key = self.data_key if self.data_key else name,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )