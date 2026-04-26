"""JSON codec — always available (stdlib only)."""
from __future__ import annotations

import json as _json

from ._common import read_source


def to(cls, obj, *, indent=None, **kwargs) -> str:
    """Serialise ``obj`` to a JSON string. ``**kwargs`` pass through to
    ``json.dumps`` (e.g. ``sort_keys=True``)."""
    return _json.dumps(cls.dump(obj), indent=indent, **kwargs)


def from_(cls, source):
    """Parse JSON ``source`` (path or string content) and load into ``cls``."""
    payload = _json.loads(read_source(source))
    if not isinstance(payload, dict):
        raise ValueError(
            f'{cls.__name__}.from_json: top-level JSON must be an object, '
            f'got {type(payload).__name__}'
        )
    return cls.load(payload)
