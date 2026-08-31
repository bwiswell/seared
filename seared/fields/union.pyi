from typing import Any

from .._core.base import Seared

# ``Union`` is an UNWRAP field. Its ``default`` names a fallback *variant*
# class (schema-evolution), not a field default — so no ``default_factory`` /
# ``missing`` are surfaced here; a Union field is always populated on load.
def Union(
    *,
    variants: dict[str, type[Seared]],
    tag_key: str = ...,
    payload_key: str | None = ...,
    default: type[Seared] | None = ...,
    data_key: str | None = ...,
    dump: bool = ...,
    doc: str | None = ...,
    required: bool = ...,
) -> Any: ...
