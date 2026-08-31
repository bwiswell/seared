# Benchmarks

Throughput comparison against `marshmallow` and `pydantic` on a
representative nested schema. Headline numbers also live on the
[README](../../README.md); this doc is the full methodology +
reproduction guide.

The bench lives in [`bench/`](../../bench/) — it commits and ships with
the repo, but not the installable package. Every recorded run writes a
machine-readable snapshot to [`bench/results.json`](../../bench/results.json);
history lives in git.

## Schema

One outer object with a 20-item list of 3-field records plus a list of
3 string tags:

```python
@s.seared
class Inner(s.Seared):
    x: int = s.Int(required=True)
    y: float = s.Float(required=True)
    label: str | None = s.Str(default=None)

@s.seared
class Outer(s.Seared):
    name: str = s.Str(required=True)
    items: list[Inner] = s.T(Inner, many=True, required=True)
    tags: list[str] = s.Str(many=True, default_factory=list)
```

```python
payload = {
    'name': 'demo',
    'items': [{'x': i, 'y': i * 1.5, 'label': f'i{i}'} for i in range(20)],
    'tags': ['alpha', 'beta', 'gamma'],
}
```

## Configurations

- **`seared` (strict)** — default `@s.seared`, equivalent to
  `validate=True`. Type checks fire on every field per call.
- **`seared` (lax)** — `@s.seared(validate=False)`. Skips type guards;
  coerces where obvious. Useful when inputs are already known-good
  (e.g. internal RPC, post-validation pipeline stages).
- **`marshmallow`** — equivalent schema using `Schema` + `Nested` +
  `List`, `unknown = EXCLUDE`. The other *pure-Python* library in the
  comparison — apples-to-apples with seared on implementation strategy.
- **`pydantic` v2** — equivalent `BaseModel`s with `extra='ignore'`,
  `model_validate` / `model_dump`. Included for scale: its core is
  compiled Rust (`pydantic-core`), so it is not an apples-to-apples
  pure-Python comparison.

20,000 iterations per (case, op), single-threaded, timed via
`time.perf_counter()` after a 5% warmup pass. All cases run the same
payload built once upfront.

## Results

Recorded 2026-08-30 — Python 3.14.3, Linux x86_64 (WSL2), laptop-class
CPU. seared 0.2.4, marshmallow 4.3.1, pydantic 2.13.5. Raw numbers:
[`bench/results.json`](../../bench/results.json).

| Op   | `marshmallow` | `seared` (strict) | `seared` (lax) | `pydantic` |
|------|---------------|-------------------|----------------|------------|
| load | 7,739 ops/s   | 28,405 ops/s (~3.7×) | 27,758 ops/s (~3.6×) | 148,995 ops/s |
| dump | 25,388 ops/s  | 44,772 ops/s (~1.8×) | 47,048 ops/s (~1.9×) | 181,317 ops/s |

Per-op timing:

| Op   | `marshmallow` | `seared` (strict) | `seared` (lax) | `pydantic` |
|------|---------------|-------------------|----------------|------------|
| load | 129 µs        | 35 µs             | 36 µs          | 6.7 µs     |
| dump | 39 µs         | 22 µs             | 21 µs          | 5.5 µs     |

Ratios in the first table are versus `marshmallow`. Earlier recorded
baselines (e.g. the 2026-04-24 run against marshmallow 3.26, where seared
led load by ~8×) are in the git history of `bench/results.json`'s
predecessors; marshmallow 4 closed part of the gap.

## Reading the results

- **Versus marshmallow** (the like-for-like pure-Python comparison),
  seared loads ~3.7× and dumps ~1.8× faster.
- **Versus pydantic**, seared is ~4–5× slower. That is the expected cost
  of pure Python versus a compiled Rust core — seared's trade is zero
  runtime dependencies and no binary wheels, not beating native code.
- **Strict versus lax is within noise on `load`** (the guards are cheap
  `isinstance` checks against builtin types) and worth a few percent on
  `dump`. Most of seared's advantage over marshmallow comes from
  per-call overhead, not validation.

## Why seared is fast (for pure Python)

- **`__slots__` everywhere.** No `__dict__` per instance; attribute access
  is a slot read.
- **No schema class layer.** Field metadata is stored as `Field` defaults
  on the dataclass; no separate `Schema` object indirection on every call.
- **Pre-baked spec tuple.** `__seared_fields__` is computed once at decorator
  time; each `dump` / `load` walks the same `(attr, wire, Field)` triples.
- **No Marshmallow `Meta` / `pre_load` / `post_dump` machinery.** The
  decorator does one simple pass per direction.
- **`format=` kwarg threading is free.** `Bytes` / `NDArray` get their
  carrier hint via `**kwargs`; other fields ignore — no per-call dispatch
  overhead.

## Reproduction

```sh
# From the repo root. Comparators are behind the `bench` extra —
# they are NOT seared dependencies.
uv sync --extra bench
uv run python -m bench
```

The runner prints an `ops/s` table and rewrites `bench/results.json`
(suppress with `--no-write`; tune with `-n`). Missing comparators are
skipped with a note, so `uv run python -m bench` also works in a plain
dev sync and times seared alone. Absolute numbers vary by machine;
relative ratios should hold across hardware.

## Caveats

- **Single-threaded, single-process.** No GIL contention, no shared-state
  serialisation overhead. Real-world throughput depends on what else the
  process is doing.
- **Static schema.** All three libraries cache schema introspection at
  class / decorator construction. Hot-path performance reflects the steady
  state; cold-start (importing seared, building the first decorated class)
  is not measured here.
- **No I/O.** The bench measures the pure transformation layer
  (dict ↔ object); JSON string encode/decode is outside the loop and
  identical between libraries.
- **Field type coverage matches the comparators.** The bench schema sticks
  to `Int` / `Float` / `Str` / nested object / list-of-objects /
  list-of-strings — types all three libraries handle natively. Fields
  exclusive to seared (`Decimal`, `Path`, `UUID`, `PandasFrame`,
  `PolarsFrame`, `NDArray`, tagged `Union`) aren't in the comparison
  because head-to-head wouldn't be meaningful.

## Future work

- **msgpack carrier benchmark.** `format='msgpack'` skips base64 for
  binary fields — significant on `Bytes`-heavy schemas.
- **DataFrame field benchmarks.** Records-form encode / decode versus
  Arrow IPC alternatives.
- **Cold-start measurements.** First-decoration cost matters for short-
  lived processes (e.g. CLI tools).
- **Table generation.** Regenerate the tables above (and the README
  headline) from `bench/results.json` instead of hand-copying.
