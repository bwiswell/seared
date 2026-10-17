from collections.abc import Callable
from typing import Any

def Tuple(
    *fields: Any,
    default: tuple | None = ...,
    default_factory: Callable[[], Any] = ...,
    data_key: str | None = ...,
    keyed: bool = ...,
    many: bool = ...,
    required: bool = ...,
    nullable: bool = ...,
    dump: bool = ...,
    doc: str | None = ...,
) -> Any: ...
