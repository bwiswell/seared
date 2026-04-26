"""Per-format codecs attached to every ``@s.seared`` class via
:func:`_attach_format_methods` (called from
``seared/_core/decorator.py::_build``).

Each codec module exposes a ``to(cls, obj)`` and ``from_(cls, source)``
pair. Optional formats (TOML write, YAML, ...) raise an informative
``ImportError`` from inside the call when the optional dependency is
missing. Detection-time imports stay fast — only the JSON codec is
actually wired at decorator time; others are looked up via ``getattr``
when the bound method runs.
"""
from __future__ import annotations

from . import csv_ as _csv_mod
from . import json_ as _json_mod
from . import toml_ as _toml_mod
from . import yaml_ as _yaml_mod


def _attach_format_methods(cls):
    """Attach per-format ``to_*`` / ``from_*`` classmethods to ``cls``.

    Called once per ``@s.seared`` class at decorator time. Each method
    is a thin shim over the format module — keeps the bound classmethod
    signatures clean while letting the codec modules do the real work.
    """
    cls.to_json   = classmethod(lambda c, obj, **kw: _json_mod.to(c, obj, **kw))
    cls.from_json = classmethod(lambda c, src: _json_mod.from_(c, src))

    cls.to_toml   = classmethod(lambda c, obj: _toml_mod.to(c, obj))
    cls.from_toml = classmethod(lambda c, src: _toml_mod.from_(c, src))

    cls.to_yaml   = classmethod(lambda c, obj: _yaml_mod.to(c, obj))
    cls.from_yaml = classmethod(lambda c, src: _yaml_mod.from_(c, src))

    cls.to_csv    = classmethod(lambda c, items: _csv_mod.to(c, items))
    cls.from_csv  = classmethod(lambda c, src: _csv_mod.from_(c, src))


__all__ = ['_attach_format_methods']
