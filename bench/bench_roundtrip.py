"""Throughput benchmark for seared load/dump.

Not collected by pytest (filename lacks the ``test_`` prefix). Run directly:

    uv run python tests/bench_roundtrip.py

Runs the same schema twice — once with ``validate=True`` (default) and once with
``validate=False`` (lax mode) — so the overhead of validation is visible.
"""
from __future__ import annotations

import time
from typing import Optional

import seared as s


def _build(validate: bool):
    @s.seared(validate=validate)
    class Inner(s.Seared):
        x: int = s.Int(required=True)
        y: float = s.Float(required=True)
        label: Optional[str] = s.Str()

    @s.seared(validate=validate)
    class Outer(s.Seared):
        name: str = s.Str(required=True)
        items: list = s.T(Inner, many=True, required=True)
        tags: list = s.Str(many=True, missing=[])

    return Outer


def _time(outer, payload, n: int) -> tuple[float, float]:
    t0 = time.perf_counter()
    for _ in range(n):
        obj = outer.load(payload)
    t_load = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(n):
        outer.dump(obj)
    t_dump = time.perf_counter() - t0
    return t_load, t_dump


def run(n: int = 20_000) -> None:
    payload = {
        'name': 'demo',
        'items': [{'x': i, 'y': i * 1.5, 'label': f'i{i}'} for i in range(20)],
        'tags': ['alpha', 'beta', 'gamma'],
    }

    for label, validate in [('validate=True ', True), ('validate=False', False)]:
        outer = _build(validate)
        t_load, t_dump = _time(outer, payload, n)
        print(
            f'{label}  load: {n / t_load:>8,.0f} ops/s  ({t_load * 1e6 / n:6.2f} us/op)   '
            f'dump: {n / t_dump:>8,.0f} ops/s  ({t_dump * 1e6 / n:6.2f} us/op)'
        )


if __name__ == '__main__':
    run()
