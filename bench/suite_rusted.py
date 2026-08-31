"""seared + the ``rusted`` compiled accelerator core.

The same schema as ``suite_seared``, decorated normally so the accelerator
seam takes it. Skipped with a note when ``rusted`` isn't installed, exactly
like the comparator suites — it is an optional extra, never a dependency.
"""

from __future__ import annotations

import rusted

import seared as s

from .harness import Case


def _build(validate: bool) -> type[s.Seared] | None:
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

    # Importable is not the same as engaged — SEARED_ACCEL=off, an ABI
    # mismatch, or a declined class would all leave this on the Python path.
    # Timing that and labelling it "rusted" is the mis-attribution this suite
    # exists to prevent, so say so and contribute nothing.
    if not Outer.__seared_accel__.accelerated:
        print(f'suite_rusted: skipped ({Outer.__seared_accel__.reason})')
        return None
    return Outer


def cases() -> list[Case]:
    """The accelerated strict/lax pair, or nothing if the seam didn't engage."""
    out = []
    for variant, validate in [('strict', True), ('lax', False)]:
        outer = _build(validate)
        if outer is None:
            return []
        out.append(
            Case(
                library='seared+rusted',
                variant=variant,
                version=f'{s.__version__}/rusted {rusted.__version__}',
                load=outer.load,
                dump=outer.dump,
            )
        )
    return out
