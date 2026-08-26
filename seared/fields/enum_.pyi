from collections.abc import Callable
from enum import Enum as _PyEnum
from typing import Any

def Enum(
    *,
    enum: type[_PyEnum],
    data_key: str | None = ...,
    keyed: bool = ...,
    many: bool = ...,
    required: bool = ...,
    dump: bool = ...,
    default: Any = ...,
    default_factory: Callable[[], Any] = ...,
    missing: Any = ...,
) -> Any: ...
