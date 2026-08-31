r"""``pathlib.Path`` field — POSIX-normalised on the wire.

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
from pathlib import Path as _Path
from pathlib import PurePath
from typing import Any

from seared._core.errors import ValidationError

from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Path(Field):
    """``pathlib.Path`` serialised as a POSIX string."""
    concrete: type = _Path

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> str:
        """``pathlib.Path`` → POSIX string (forward slashes on every OS)."""
        if not isinstance(value, PurePath):
            if validate:
                msg = f'expected pathlib.Path, got {type(value).__name__}'
                raise ValidationError(msg)
            return value
        # ``as_posix()`` converts any PurePath subclass to a forward-slash
        # string. A Windows ``PureWindowsPath('C:\\foo')`` becomes
        # ``'C:/foo'`` regardless of which OS we're running on.
        return value.as_posix()

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:
        """POSIX string → an instance of the ``concrete`` path class."""
        if isinstance(value, PurePath):
            return value
        if not isinstance(value, str):
            if validate:
                msg = f'expected str path, got {type(value).__name__}'
                raise ValidationError(msg)
            return value
        return self.concrete(value)
