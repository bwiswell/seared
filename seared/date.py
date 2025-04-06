from dataclasses import dataclass
from datetime import date
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Date as MDate, Field

from .field import Field, FieldMeta


@dataclass(frozen=True)
class DateMeta(Field):
    format: Optional[str] = None
    missing: Optional[date] = None
    

@dataclass(frozen=True)
class Date(FieldMeta, DateMeta):

    def to_field (self, _: str) -> Field:
        return self.wrap(
            lambda **kws: MDate(format=self.format, **kws),
            data_key = self.data_key,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )