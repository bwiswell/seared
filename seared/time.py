from dataclasses import dataclass
from datetime import time
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Field, Time as MTime

from .field import Field, FieldMeta


@dataclass(frozen=True)
class TimeMeta(Field):
    format: Optional[str] = None
    missing: Optional[time] = None
    

@dataclass(frozen=True)
class Time(FieldMeta, TimeMeta):

    def to_field (self, _: str) -> Field:
        return self.wrap(
            lambda *kws: MTime(format=self.format, **kws),
            data_key = self.data_key,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )