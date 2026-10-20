from collections.abc import Callable
from typing import Any

def Int(
    *,
    ge: int | None = ...,
    gt: int | None = ...,
    le: int | None = ...,
    lt: int | None = ...,
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

# Not a field: ``Int``'s float and numeric-string coercion, which an
# int-valued ``Enum`` shares. ``None`` when the rules refuse the value.
def coerce_int(value: Any, validate: bool) -> int | None: ...
