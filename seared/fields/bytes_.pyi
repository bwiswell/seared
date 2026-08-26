from collections.abc import Callable
from typing import Any, Literal

def Bytes(
    *,
    encoding: Literal['base64', 'hex'] = ...,
    data_key: str | None = ...,
    keyed: bool = ...,
    many: bool = ...,
    required: bool = ...,
    dump: bool = ...,
    default: Any = ...,
    default_factory: Callable[[], Any] = ...,
    missing: Any = ...,
) -> Any: ...
