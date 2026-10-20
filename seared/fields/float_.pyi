from collections.abc import Callable
from typing import Any

def Float(
    *,
    ge: float | None = ...,
    gt: float | None = ...,
    le: float | None = ...,
    lt: float | None = ...,
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
