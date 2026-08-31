"""Shared bench harness: workload, timing loop, and the results schema.

The ``Report`` / ``Measurement`` classes are seared classes on purpose —
the bench dogfoods the library it measures to produce its own artifact.
"""

from __future__ import annotations

import platform
import time
from dataclasses import dataclass
from importlib.metadata import version as dist_version
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import seared as s

#: Iterations per (case, op). Matches the historical bench baseline so
#: numbers stay comparable across releases.
DEFAULT_ITERATIONS = 20_000

#: Fraction of the timed iteration count spent warming up each callable
#: before measurement (caches, allocator, pydantic-core lazy init).
WARMUP_FRACTION = 0.05


def payload() -> dict[str, Any]:
    """The representative nested payload every suite loads and dumps."""
    return {
        'name': 'demo',
        'items': [{'x': i, 'y': i * 1.5, 'label': f'i{i}'} for i in range(20)],
        'tags': ['alpha', 'beta', 'gamma'],
    }


@dataclass(frozen=True, slots=True)
class Case:
    """One (library, variant) configuration to be timed."""

    library: str
    variant: str
    version: str
    load: Callable[[dict[str, Any]], Any]
    dump: Callable[[Any], dict[str, Any]]


@s.seared
class Measurement(s.Seared):
    """One timed (case, op) result."""

    library: str = s.Str(required=True)
    variant: str = s.Str(required=True)
    version: str = s.Str(required=True)
    op: str = s.Str(required=True, doc="'load' or 'dump'")
    ops_per_s: float = s.Float(required=True)
    us_per_op: float = s.Float(required=True)


@s.seared
class Report(s.Seared):
    """The committed ``bench/results.json`` artifact."""

    timestamp: str = s.Str(required=True, doc='UTC ISO 8601')
    python: str = s.Str(required=True)
    platform: str = s.Str(required=True)
    iterations: int = s.Int(required=True)
    measurements: list[Measurement] = s.T(Measurement, many=True, required=True)


def run_case(case: Case, data: dict[str, Any], n: int) -> list[Measurement]:
    """Time ``case.load`` / ``case.dump`` over ``n`` iterations each."""
    warmup = max(1, int(n * WARMUP_FRACTION))

    for _ in range(warmup):
        obj = case.load(data)
    t0 = time.perf_counter()
    for _ in range(n):
        obj = case.load(data)
    t_load = time.perf_counter() - t0

    for _ in range(warmup):
        case.dump(obj)
    t0 = time.perf_counter()
    for _ in range(n):
        case.dump(obj)
    t_dump = time.perf_counter() - t0

    return [
        Measurement(
            library=case.library,
            variant=case.variant,
            version=case.version,
            op=op,
            ops_per_s=n / t,
            us_per_op=t * 1e6 / n,
        )
        for op, t in [('load', t_load), ('dump', t_dump)]
    ]


def environment() -> tuple[str, str]:
    """(python version, platform string) for the report metadata."""
    return platform.python_version(), platform.platform()


__all__ = [
    'DEFAULT_ITERATIONS',
    'Case',
    'Measurement',
    'Report',
    'dist_version',
    'environment',
    'payload',
    'run_case',
]
