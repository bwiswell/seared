from collections.abc import Callable
from pathlib import PurePath
from typing import Any

def Path(
    *,
    concrete: type[PurePath] = ...,
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
