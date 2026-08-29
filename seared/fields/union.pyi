from typing import Any

# ``Union`` is an UNWRAP field. Its ``default`` names a fallback *variant*
# class (schema-evolution), not a field default — so no ``default_factory`` /
# ``missing`` are surfaced here; a Union field is always populated on load.
def Union(
    *,
    variants: dict[str, type],
    tag_key: str = ...,
    payload_key: str | None = ...,
    default: type | None = ...,
    data_key: str | None = ...,
    dump: bool = ...,
    doc: str | None = ...,
    required: bool = ...,
) -> Any: ...
