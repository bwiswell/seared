from dataclasses import dataclass
from datetime import time
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Field as MField, Time as MTime

from .field import Field


@dataclass(frozen=True)
class TimeMeta:
    format: Optional[str] = None
    missing: Optional[time] = None
    

@dataclass(frozen=True)
class Time(Field, TimeMeta):

    def to_field (self, name: str) -> MField:
        return self.wrap(
            lambda **kws: MTime(format=self.format, **kws),
            data_key = self.data_key if self.data_key else name,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )