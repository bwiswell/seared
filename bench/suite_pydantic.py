"""pydantic v2 case — equivalent model, apples-to-apples with seared.

pydantic is not a seared dependency; install via ``uv sync --extra bench``.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .harness import Case, dist_version


class Inner(BaseModel):
    model_config = ConfigDict(extra='ignore')

    x: int
    y: float
    label: str | None = None


class Outer(BaseModel):
    model_config = ConfigDict(extra='ignore')

    name: str
    items: list[Inner]
    tags: list[str] = []


def cases() -> list[Case]:
    """The pydantic v2 comparator case."""
    return [Case(
        library='pydantic', variant='default', version=dist_version('pydantic'),
        load=Outer.model_validate, dump=lambda obj: obj.model_dump(),
    )]
