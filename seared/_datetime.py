from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from marshmallow import missing
from marshmallow.fields import DateTime as MDateTime, Field

from .field import Field


@dataclass(frozen=True)
class DateTimeMeta:
    format: Optional[str] = None
    missing: Optional[datetime] = None
    

@dataclass(frozen=True)
class DateTime(Field, DateTimeMeta):

    def to_field (self, name: str) -> Field:
        return self.wrap(
            lambda **kws: MDateTime(format=self.format, **kws),
            data_key = self.data_key if self.data_key else name,
            load_only = not self.write,
            load_default = self._load_default(missing)
        )