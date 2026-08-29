from collections.abc import Callable
from typing import Any

def Tuple(
    *fields: Any,
    default: tuple | None = ...,
    default_factory: Callable[[], Any] = ...,
    missing: tuple | None = ...,
    data_key: str | None = ...,
    keyed: bool = ...,
    many: bool = ...,
    required: bool = ...,
    dump: bool = ...,
    doc: str | None = ...,
) -> Any: ...
