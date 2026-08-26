from __future__ import annotations

from dataclasses import dataclass

from .._core.errors import ValidationError
from .field import Field

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False


@dataclass(frozen=True, kw_only=True, slots=True)
class NDArray(Field):
    def __post_init__(self):
        super().__post_init__()
        if not _NUMPY_AVAILABLE:
            raise ImportError(
                "seared.NDArray requires numpy. "
                "Install it with: uv add 'seared[numpy]'"
            )

    def serialize(self, value, validate: bool = True, **kwargs):
        if not isinstance(value, np.ndarray):
            if validate:
                raise ValidationError(f'expected ndarray, got {type(value).__name__}')
            return value
        return value.tolist()

    def deserialize(self, value, validate: bool = True, **kwargs):
        return np.array(value)
