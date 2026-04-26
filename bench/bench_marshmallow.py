"""Equivalent marshmallow benchmark — apples-to-apples comparison for bench_roundtrip.py.

marshmallow is NOT a seared dependency; install it ad-hoc before running:
    uv pip install 'marshmallow>=3.26.1,<4.0'
    uv run python tests/bench_marshmallow.py

Recorded baseline (2026-04-24, same machine as bench_roundtrip.py):
    marshmallow   load:  4,743 ops/s   (211 us/op)
    marshmallow   dump: 16,042 ops/s   ( 62 us/op)
    seared strict load: 37,454 ops/s   ( 27 us/op)   ~7.9x faster
    seared strict dump: 42,338 ops/s   ( 24 us/op)   ~2.6x faster
    seared lax    load: 37,905 ops/s   ( 26 us/op)   ~8.0x faster
    seared lax    dump: 48,988 ops/s   ( 20 us/op)   ~3.1x faster
"""
from __future__ import annotations

import time

from marshmallow import Schema, post_load, EXCLUDE
from marshmallow.fields import Integer, Float as MFloat, List as MList, Nested, String


class InnerSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    x = Integer(required=True)
    y = MFloat(required=True)
    label = String(load_default=None)


class OuterSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = String(required=True)
    items = MList(Nested(InnerSchema()), required=True)
    tags = MList(String(), load_default=[])


def run(n: int = 20_000) -> None:
    payload = {
        'name': 'demo',
        'items': [{'x': i, 'y': i * 1.5, 'label': f'i{i}'} for i in range(20)],
        'tags': ['alpha', 'beta', 'gamma'],
    }

    schema = OuterSchema()

    t0 = time.perf_counter()
    for _ in range(n):
        loaded = schema.load(payload)
    t_load = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(n):
        schema.dump(loaded)
    t_dump = time.perf_counter() - t0

    print(f'marshmallow load: {n / t_load:,.0f} ops/s  ({t_load * 1e6 / n:.2f} us/op)')
    print(f'marshmallow dump: {n / t_dump:,.0f} ops/s  ({t_dump * 1e6 / n:.2f} us/op)')


if __name__ == '__main__':
    run()
