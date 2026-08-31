"""YAML codec.

Both directions go through the optional ``seared[yaml]`` extra (lazy
``PyYAML`` import).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import os
    from types import ModuleType

    from seared._core.base import Seared

from ._common import read_source


def _import_yaml() -> ModuleType:
    try:
        import yaml
    except ImportError as e:
        msg = (
            "to_yaml/from_yaml requires PyYAML — install via "
            "`pip install seared[yaml]` (or `uv add 'seared[yaml]'`)."
        )
        raise ImportError(msg) from e
    else:
        return yaml


def to(cls: type[Seared], obj: Seared) -> str:
    """Serialise ``obj`` to a YAML string."""
    yaml = _import_yaml()
    return yaml.safe_dump(cls.dump(obj), sort_keys=False)


def from_(cls: type[Seared], source: str | os.PathLike) -> Seared:
    """Parse YAML ``source`` (path or string content) and load into ``cls``."""
    yaml = _import_yaml()
    payload = yaml.safe_load(read_source(source))
    # ValueError, not TypeError: the malformed-payload contract is pinned
    # by tests and inherited by SearedError (itself a ValueError).
    if not isinstance(payload, dict):
        msg = (
            f'{cls.__name__}.from_yaml: top-level YAML must be a mapping, '
            f'got {type(payload).__name__}'
        )
        raise ValueError(msg)  # noqa: TRY004
    return cls.load(payload)
