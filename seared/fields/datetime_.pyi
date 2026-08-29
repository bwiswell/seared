from collections.abc import Callable
from typing import Any

def DateTime(
    *,
    format: str | None = ...,
    data_key: str | None = ...,
    keyed: bool = ...,
    many: bool = ...,
    required: bool = ...,
    dump: bool = ...,
    doc: str | None = ...,
    default: Any = ...,
    default_factory: Callable[[], Any] = ...,
    missing: Any = ...,
) -> Any: ...
