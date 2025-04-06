from dataclasses import dataclass
from typing import Optional

from marshmallow.fields import Bool as MBool, Field

from .field import Field, FieldMeta


@dataclass(frozen=True)
class BoolMeta(Field):
    missing: Optional[bool] = None


@dataclass(frozen=True)
class Bool(FieldMeta, BoolMeta):

    def to_field (self, _: str) -> Field:
        return self.wrap(
            MBool,
            data_key = self.data_key,
            load_only = not self.write,
            missing = self.missing
        )