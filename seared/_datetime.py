from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from marshmallow.fields import DateTime as MDateTime, Field

from .field import Field, FieldMeta


@dataclass(frozen=True)
class DateTimeMeta(Field):
    format: Optional[str] = None
    missing: Optional[datetime] = None
    

@dataclass(frozen=True)
class DateTime(DateTimeMeta, FieldMeta):

    def to_field (self, _: str) -> Field:
        return self.wrap(
            lambda *kws: MDateTime(format=self.format, **kws),
            data_key = self.data_key,
            load_only = not self.write,
            missing = self.missing
        )