from dataclasses import dataclass
from typing import Any, Optional

from marshmallow import missing
from marshmallow.fields import Field as MField, Function
import numpy as np

from .field import Field


@dataclass(frozen=True)
class NDArrayMeta:
    missing: Optional[np.ndarray] = None


@dataclass(frozen=True)
class NDArray(Field, NDArrayMeta):

    def to_field (self, name: str) -> MField:
        i = 0
        def deserialize (value: list[Any]) -> np.ndarray:
            return np.array(value)
        def serialize (cls: object) -> Optional[list[Any]]:
            nonlocal i
            value: Optional[np.ndarray] = cls.__getattribute__(name)
            if value is None: return None
            if self.many:
                out = [val.tolist() for val in value[i]]
                i += 1
                return out
            else:
                return value.tolist()
        return self.wrap(
            lambda **kws: Function(
                serialize = serialize,
                deserialize = deserialize,
                **kws
            ),
            data_key = self.data_key if self.data_key else name,
            load_only = not self.write,
            missing = missing if self.required else self.missing
        )