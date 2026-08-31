from collections.abc import Callable
from typing import Any

from seared._core.base import Seared

def T(
    schema: type[Seared],
    *,
    default: Any = ...,
    default_factory: Callable[[], Any] = ...,
    missing: Any = ...,
    data_key: str | None = ...,
    keyed: bool = ...,
    many: bool = ...,
    required: bool = ...,
    dump: bool = ...,
    doc: str | None = ...,
) -> Any: ...
