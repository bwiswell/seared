from dataclasses import dataclass
from typing import Optional, TypeVar

from marshmallow.fields import Field


T = TypeVar('T')


@dataclass(frozen=True)
class Field:
    data_key: str

    def to_field (self, name: str) -> Field:
        raise NotImplementedError