"""JSON codec — always available (stdlib only)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import os

    from seared._core.base import Seared

import json as _json

from ._common import read_source


def to(cls: type[Seared], obj: Seared, *, indent: int | None = None, **kwargs: Any) -> str:
    """Serialise ``obj`` to a JSON string.

    ``**kwargs`` pass through to ``json.dumps`` (e.g. ``sort_keys=True``).
    """
    return _json.dumps(cls.dump(obj), indent=indent, **kwargs)


def from_(cls: type[Seared], source: str | os.PathLike) -> Seared:
    """Parse JSON ``source`` (path or string content) and load into ``cls``."""
    payload = _json.loads(read_source(source))
    # ValueError, not TypeError: the malformed-payload contract is pinned
    # by tests and inherited by SearedError (itself a ValueError).
    if not isinstance(payload, dict):
        msg = f'{cls.__name__}.from_json: top-level JSON must be an object, got {type(payload).__name__}'
        raise ValueError(msg)  # noqa: TRY004
    return cls.load(payload)
