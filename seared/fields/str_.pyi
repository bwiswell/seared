from collections.abc import Callable
from typing import Any

def Str(
    *,
    min_length: int | None = ...,
    max_length: int | None = ...,
    pattern: str | None = ...,
    data_key: str | None = ...,
    keyed: bool = ...,
    many: bool = ...,
    required: bool = ...,
    nullable: bool = ...,
    dump: bool = ...,
    doc: str | None = ...,
    default: Any = ...,
    default_factory: Callable[[], Any] = ...,
) -> Any: ...
