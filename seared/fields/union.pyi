from typing import Any

from seared._core.base import Seared

# ``Union`` is an UNWRAP field, always populated on load. ``fallback`` names
# the variant an unknown tag falls back to (schema evolution). ``default`` is
# accepted only as ``None``: a Union has no default value, and anything else
# raises ``TypeError`` (until 0.4.0, ``default=`` named the fallback). It stays
# in the signature because PEP 681 keys a field's optionality off it.
def Union(
    *,
    variants: dict[str, type[Seared]],
    tag_key: str = ...,
    payload_key: str | None = ...,
    fallback: type[Seared] | None = ...,
    default: None = ...,
    data_key: str | None = ...,
    dump: bool = ...,
    doc: str | None = ...,
    required: bool = ...,
) -> Any: ...
