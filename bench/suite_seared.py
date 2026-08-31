"""seared cases: strict (default) and lax (``validate=False``)."""

from __future__ import annotations

import seared as s

from .harness import Case


def _build(validate: bool) -> type[s.Seared]:
    @s.seared(validate=validate)
    class Inner(s.Seared):
        x: int = s.Int(required=True)
        y: float = s.Float(required=True)
        label: str | None = s.Str(default=None)

    @s.seared(validate=validate)
    class Outer(s.Seared):
        name: str = s.Str(required=True)
        items: list[Inner] = s.T(Inner, many=True, required=True)
        tags: list[str] = s.Str(many=True, default_factory=list)

    return Outer


def cases() -> list[Case]:
    """The seared cases — one strict, one lax (``validate=False``)."""
    out = []
    for variant, validate in [('strict', True), ('lax', False)]:
        outer = _build(validate)
        out.append(
            Case(
                library='seared',
                variant=variant,
                version=s.__version__,
                load=outer.load,
                dump=outer.dump,
            )
        )
    return out
