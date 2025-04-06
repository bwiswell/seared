from dataclasses import dataclass
from typing import Callable, TypeVar

from marshmallow.fields import Dict, Field, List, String


T = TypeVar('T')


@dataclass(frozen=True)
class Field:
    data_key: str

    def wrap (
                self, 
                field: Callable[..., Field], 
                keyed: bool,
                many: bool,
                **kwargs
            ) -> Field:
        if self.keyed:
            return Dict(String(), field(), **kwargs)
        elif self.many:
            return List(field(), **kwargs)
        else:
            return field(**kwargs)

    def to_field (self, name: str) -> Field:
        raise NotImplementedError