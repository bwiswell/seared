from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from seared._core.errors import ValidationError

from .field import Field

try:
    import numpy as np

    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False


@dataclass(frozen=True, kw_only=True, slots=True)
class NDArray(Field):
    def __post_init__(self) -> None:
        """Fail fast when the ``seared[numpy]`` extra isn't installed."""
        super().__post_init__()
        if not _NUMPY_AVAILABLE:
            msg = "seared.NDArray requires numpy. Install it with: uv add 'seared[numpy]'"
            raise ImportError(msg)

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:
        """``numpy.ndarray`` → nested lists."""
        if not isinstance(value, np.ndarray):
            if validate:
                msg = f'expected ndarray, got {type(value).__name__}'
                raise ValidationError(msg)
            return value
        return value.tolist()

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:  # noqa: ARG002 — signature fixed by Field
        """Nested lists → ``numpy.ndarray``."""
        return np.array(value)
