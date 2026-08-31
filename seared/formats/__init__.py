"""Per-format codecs attached to every ``@s.seared`` class.

Wiring happens in :func:`_attach_format_methods`, called from
``seared/_core/decorator.py::_build``.

Each codec module exposes a ``to(cls, obj)`` and ``from_(cls, source)``
pair. Optional formats (TOML write, YAML, ...) raise an informative
``ImportError`` from inside the call when the optional dependency is
missing. Detection-time imports stay fast — only the JSON codec is
actually wired at decorator time; others are looked up via ``getattr``
when the bound method runs.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from seared._core.base import Seared

from . import csv_ as _csv_mod
from . import json_ as _json_mod
from . import toml_ as _toml_mod
from . import yaml_ as _yaml_mod


def _attach_format_methods(cls: type[Seared]) -> None:
    """Attach per-format ``to_*`` / ``from_*`` classmethods to ``cls``.

    Called once per ``@s.seared`` class at decorator time. Each method
    is a thin shim over the format module — keeps the bound classmethod
    signatures clean while letting the codec modules do the real work.

    The assignments are deliberate runtime monkey-patching: ``Seared``
    already declares each ``to_*`` / ``from_*`` for the static surface, so
    ty sees a plain method where a ``classmethod`` object lands. Silenced
    per-line rather than by loosening the parameter type.
    """
    cls.to_json   = classmethod(_json_mod.to)  # ty: ignore[invalid-assignment]
    cls.from_json = classmethod(_json_mod.from_)  # ty: ignore[invalid-assignment]

    cls.to_toml   = classmethod(_toml_mod.to)  # ty: ignore[invalid-assignment]
    cls.from_toml = classmethod(_toml_mod.from_)  # ty: ignore[invalid-assignment]

    cls.to_yaml   = classmethod(_yaml_mod.to)  # ty: ignore[invalid-assignment]
    cls.from_yaml = classmethod(_yaml_mod.from_)  # ty: ignore[invalid-assignment]

    cls.to_csv    = classmethod(_csv_mod.to)  # ty: ignore[invalid-assignment]
    cls.from_csv  = classmethod(_csv_mod.from_)  # ty: ignore[invalid-assignment]


__all__ = ['_attach_format_methods']
