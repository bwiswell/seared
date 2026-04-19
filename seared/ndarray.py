from dataclasses import dataclass
from typing import Any, Optional

from marshmallow import missing
from marshmallow.fields import Field as MField
import numpy as np

from .field import Field


@dataclass(frozen=True)
class NDArrayMeta:
    missing: Optional[np.ndarray] = None


@dataclass(frozen=True)
class NDArray(Field, NDArrayMeta):

    def to_field (self, name: str) -> MField:
        class NDArrayField(MField):
            def _serialize (self, value, attr, obj, **kwargs):
                if value is None: return None
                return value.tolist()

            def _deserialize (self, value, attr, data, **kwargs):
                return np.array(value)

        return self.wrap(
            NDArrayField,
            data_key = self.data_key if self.data_key else name,
            load_only = not self.write,
            load_default = self._load_default(missing)
        )
