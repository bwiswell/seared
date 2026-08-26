from collections.abc import Callable
from typing import Any

def T(
    schema: type[Any],
    *,
    default: Any = ...,
    default_factory: Callable[[], Any] = ...,
    missing: Any = ...,
    data_key: str | None = ...,
    keyed: bool = ...,
    many: bool = ...,
    required: bool = ...,
    dump: bool = ...,
) -> Any: ...
