"""Fixture models exercising every field kind the doc generator handles."""

from __future__ import annotations

import enum

import seared as s


class Band(enum.Enum):
    UHF = 0
    HF = 1


@s.seared
class Inner(s.Seared):
    """An inner value."""

    x: int = s.Int(default=0, doc='the x')


@s.seared
class StartCmd(s.Seared):
    """Start command."""

    speed: int = s.Int(required=True)


@s.seared
class Demo(s.Seared):
    """A demo model.

    Second paragraph.
    """

    source: str = s.Str(required=True, doc='origin | system')
    band: Band = s.Enum(enum=Band, default=Band.UHF, doc='freq band')
    tags: list[int] = s.Int(many=True, default_factory=list)
    ratios: dict[str, float] = s.Float(keyed=True, default_factory=dict)
    inner: Inner = s.T(Inner, required=True)
    note: str | None = s.Str(default=None, data_key='n')
    hidden: str = s.Str(default='x', dump=False)
    action: StartCmd = s.Union(variants={'start': StartCmd}, tag_key='type')
