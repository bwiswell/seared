"""``pathlib.Path`` field — POSIX-normalised on the wire.

Always serialises as forward-slash strings via ``PurePosixPath``, so a
Windows ``WindowsPath('C:\\foo')`` rounds through as ``'C:/foo'``. The
wire form is cross-platform deterministic; no leak of host path-style.

On deserialise the value is parsed by the host's native ``Path``
constructor (``PosixPath`` on Linux, ``WindowsPath`` on Windows). For
paths that should stay POSIX regardless of host (rare — most consumers
want the native), pass ``concrete=PurePosixPath``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path as _Path, PurePath, PurePosixPath
from typing import Type

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Path(Field):
    """``pathlib.Path`` serialised as a POSIX string."""
    concrete: Type = _Path

    def serialize(self, value, validate: bool = True, **kwargs) -> str:
        if not isinstance(value, PurePath):
            if validate:
                raise ValidationError(
                    f'expected pathlib.Path, got {type(value).__name__}'
                )
            return value
        # ``as_posix()`` converts any PurePath subclass to a forward-slash
        # string. A Windows ``PureWindowsPath('C:\\foo')`` becomes
        # ``'C:/foo'`` regardless of which OS we're running on.
        return value.as_posix()

    def deserialize(self, value, validate: bool = True, **kwargs):
        if isinstance(value, PurePath):
            return value
        if not isinstance(value, str):
            if validate:
                raise ValidationError(
                    f'expected str path, got {type(value).__name__}'
                )
            return value
        return self.concrete(value)
