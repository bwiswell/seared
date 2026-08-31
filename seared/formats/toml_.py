"""TOML codec.

Read via stdlib ``tomllib`` (Python ≥ 3.11); write via the optional
``tomli-w`` extra.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import os

    from seared._core.base import Seared

import tomllib

from ._common import read_source


def to(cls: type[Seared], obj: Seared) -> str:
    """Serialise ``obj`` to a TOML string.

    Requires the ``seared[toml]`` extra (lazy-imports ``tomli-w``).
    """
    try:
        import tomli_w
    except ImportError as e:
        msg = (
            "to_toml requires tomli-w — install via "
            "`pip install seared[toml]` (or `uv add 'seared[toml]'`). "
            "Reading TOML works without the extra (uses stdlib tomllib)."
        )
        raise ImportError(msg) from e
    return tomli_w.dumps(cls.dump(obj))


def from_(cls: type[Seared], source: str | os.PathLike) -> Seared:
    """Parse TOML ``source`` (path or string content) and load into ``cls``.

    Read uses stdlib ``tomllib`` — no extra required.
    """
    payload = tomllib.loads(read_source(source))
    # ValueError, not TypeError: the malformed-payload contract is pinned
    # by tests and inherited by SearedError (itself a ValueError).
    if not isinstance(payload, dict):
        msg = (
            f'{cls.__name__}.from_toml: top-level TOML must be a table, '
            f'got {type(payload).__name__}'
        )
        raise ValueError(msg)  # noqa: TRY004
    return cls.load(payload)
