"""A fixture whose model refers to a decorated class without the ``Seared`` base, and to a variant with no fields."""

from __future__ import annotations

import seared as s


@s.seared
class Bare:
    """Decorated, but not a ``Seared`` subclass."""

    n: int = s.Int(default=0, doc='a count')


@s.seared
class Go(s.Seared):
    """Move."""

    speed: int = s.Int(default=0, doc='metres per second')


@s.seared
class Stop(s.Seared):
    """Stop now. No fields."""


@s.seared
class Command(s.Seared):
    """A command, and what it carries."""

    inner: Bare | None = s.T(Bare, default=None, doc='the payload')
    cmd: Go | Stop = s.Union(variants={'go': Go, 'stop': Stop}, doc='what to do')
