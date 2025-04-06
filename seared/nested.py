from dataclasses import dataclass
from enum import Enum as PEnum
from typing import Any, Optional, TypeVar, Union

from marshmallow import Schema
from marshmallow.fields import Field, Nexted

from .field import Field


T = TypeVar('T', bound=object)


@dataclass(frozen=True)
class Nested(Field):
    schema: Schema
    missing: Optional[T] = None

    def to_field (self, _: str) -> Field:
        return Nested(
            schema = self.schema,
            data_key = self.data_key,
            missing = self.missing
        )