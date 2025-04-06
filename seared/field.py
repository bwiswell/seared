from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

from marshmallow.fields import Dict, Field, List, String


T = TypeVar('T')


@dataclass(frozen=True)
class Field:
    data_key: Optional[str] = None
    keyed: bool = False
    many: bool = False
    required: bool = False
    write: bool = True

    def wrap (
                self, 
                field: Callable[..., Field],
                **kwargs
            ) -> Field:
        if self.keyed:
            return Dict(String(), field(), **kwargs, required=self.required)
        elif self.many:
            return List(field(), **kwargs, required=self.required)
        else:
            return field(**kwargs, required=self.required)

    def to_field (self, name: str) -> Field:
        raise NotImplementedError