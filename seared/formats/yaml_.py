"""YAML codec — both directions via the optional ``seared[yaml]`` extra
(lazy ``PyYAML`` import)."""
from __future__ import annotations

from ._common import read_source


def _import_yaml():
    try:
        import yaml
        return yaml
    except ImportError as e:
        raise ImportError(
            "to_yaml/from_yaml requires PyYAML — install via "
            "`pip install seared[yaml]` (or `uv add 'seared[yaml]'`)."
        ) from e


def to(cls, obj) -> str:
    """Serialise ``obj`` to a YAML string."""
    yaml = _import_yaml()
    return yaml.safe_dump(cls.dump(obj), sort_keys=False)


def from_(cls, source):
    """Parse YAML ``source`` (path or string content) and load into ``cls``."""
    yaml = _import_yaml()
    payload = yaml.safe_load(read_source(source))
    if not isinstance(payload, dict):
        raise ValueError(
            f'{cls.__name__}.from_yaml: top-level YAML must be a mapping, '
            f'got {type(payload).__name__}'
        )
    return cls.load(payload)
