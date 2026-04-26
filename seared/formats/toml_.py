"""TOML codec — read via stdlib ``tomllib`` (Python ≥ 3.11), write via
optional ``tomli-w`` extra."""
from __future__ import annotations

import tomllib

from ._common import read_source


def to(cls, obj) -> str:
    """Serialise ``obj`` to a TOML string. Requires the ``seared[toml]``
    extra (lazy-imports ``tomli-w``)."""
    try:
        import tomli_w
    except ImportError as e:
        raise ImportError(
            "to_toml requires tomli-w — install via "
            "`pip install seared[toml]` (or `uv add 'seared[toml]'`). "
            "Reading TOML works without the extra (uses stdlib tomllib)."
        ) from e
    return tomli_w.dumps(cls.dump(obj))


def from_(cls, source):
    """Parse TOML ``source`` (path or string content) and load into ``cls``.

    Read uses stdlib ``tomllib`` — no extra required.
    """
    payload = tomllib.loads(read_source(source))
    if not isinstance(payload, dict):
        raise ValueError(
            f'{cls.__name__}.from_toml: top-level TOML must be a table, '
            f'got {type(payload).__name__}'
        )
    return cls.load(payload)
