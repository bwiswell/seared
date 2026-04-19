from dataclasses import dataclass
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Dict as MDict, Field as MField

from .field import Field


@dataclass(frozen=True)
class DictMeta:
    missing: Optional[dict] = None


@dataclass(frozen=True)
class Dict(Field, DictMeta):

    def to_field (self, name: str) -> MField:
        return self.wrap(
            MDict,
            data_key = self.data_key if self.data_key else name,
            load_only = not self.write,
            load_default = self._load_default(missing)
        )
