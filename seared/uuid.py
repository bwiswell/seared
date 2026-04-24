from dataclasses import dataclass
import uuid as _uuid
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Field as MField, UUID as MUUID

from .field import Field


@dataclass(frozen=True)
class UUIDMeta:
    missing: Optional[_uuid.UUID] = None


@dataclass(frozen=True)
class UUID(Field, UUIDMeta):

    def to_field(self, name: str) -> MField:
        return self.wrap(
            MUUID,
            data_key=self.data_key if self.data_key else name,
            load_only=not self.dump,
            load_default=self._load_default(missing)
        )
