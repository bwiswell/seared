from dataclasses import dataclass
from typing import Any, Optional, TypeVar, Union

from marshmallow import Schema, missing
from marshmallow.fields import Field as MField, Nested

from .field import Field


TT = TypeVar('TT', bound=object)


@dataclass(frozen=True)
class TMeta:
    schema: Any  # Seared subclass or marshmallow Schema instance
    missing: Optional[TT] = None


@dataclass(frozen=True)
class T(Field, TMeta):

    def to_field(self, name: str) -> MField:
        schema = self.schema.SCHEMA if hasattr(self.schema, 'SCHEMA') else self.schema
        return self.wrap(
            lambda **kws: Nested(schema, allow_none=True, **kws),
            data_key=self.data_key if self.data_key else name,
            load_only=not self.dump,
            load_default=self._load_default(missing)
        )
