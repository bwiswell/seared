"""TOML codec.

Read via stdlib ``tomllib`` (Python ≥ 3.11); write via the optional
``tomli-w`` extra.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
            'to_toml requires tomli-w — install via '
            "`pip install seared[toml]` (or `uv add 'seared[toml]'`). "
            'Reading TOML works without the extra (uses stdlib tomllib).'
        )
        raise ImportError(msg) from e
    return tomli_w.dumps(_without_nulls(cls.dump(obj)))


def _without_nulls(value: Any) -> Any:
    """``value`` with every ``None``-valued key left out, at any depth.

    TOML has no null, so a nullable field's ``None`` (or a ``Dict`` value's)
    is written as an absent key, which is how ``load`` reads it back. A
    ``None`` *element* of an array has no such reading, and is left for
    ``tomli-w`` to reject.
    """
    if isinstance(value, dict):
        return {k: _without_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_without_nulls(v) for v in value]
    return value


def from_(cls: type[Seared], source: str | os.PathLike) -> Seared:
    """Parse TOML ``source`` (path or string content) and load into ``cls``.

    Read uses stdlib ``tomllib`` — no extra required.
    """
    payload = tomllib.loads(read_source(source))
    # ValueError, not TypeError: the malformed-payload contract is pinned
    # by tests and inherited by SearedError (itself a ValueError).
    if not isinstance(payload, dict):
        msg = f'{cls.__name__}.from_toml: top-level TOML must be a table, got {type(payload).__name__}'
        raise ValueError(msg)  # noqa: TRY004
    return cls.load(payload)
