from dataclasses import dataclass
from datetime import date
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Date as MDate, Field as MField

from .field import Field


@dataclass(frozen=True)
class DateMeta:
    format: Optional[str] = None
    missing: Optional[date] = None
    

@dataclass(frozen=True)
class Date(Field, DateMeta):

    def to_field (self, name: str) -> MField:
        return self.wrap(
            lambda **kws: MDate(format=self.format, **kws),
            data_key = self.data_key if self.data_key else name,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )