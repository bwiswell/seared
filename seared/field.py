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
    dump: bool = True

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

    def _load_default (self, marshmallow_missing):
        '''
        Returns the appropriate ``load_default`` value for the marshmallow
        field: the marshmallow sentinel (meaning "required, no default") when
        ``self.required`` is ``True``, otherwise the user-specified
        ``self.missing`` value (which defaults to ``None``).
        '''
        return marshmallow_missing if self.required else self.missing

    def to_field (self, name: str) -> Field:
        raise NotImplementedError