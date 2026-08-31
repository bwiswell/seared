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
- **`seared+rusted`** — the same schema with the optional compiled
  accelerator core installed. Not a different library: identical seared
  classes, with `load` / `dump` swapped for compiled equivalents. Skipped
  with a note when `rusted` isn't installed.
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

**The `seared` cases are pinned `accel=False`.** Otherwise an accelerator
wheel that happened to be installed in the benching environment would
silently retarget them, and compiled numbers would be recorded under
seared's own name. The accelerated path is measured only by
`seared+rusted`, which in turn asserts the seam actually engaged before
contributing a case — `import rusted` succeeding is not the same as a class
being accelerated.

## Results

Recorded 2026-08-31 — Python 3.14.3, Linux x86_64 (WSL2), laptop-class
CPU. seared 0.3.0, rusted 0.1.2, marshmallow 4.3.1, pydantic 2.13.5. Raw
numbers: [`bench/results.json`](../../bench/results.json).

| Op   | `marshmallow` | `seared` (strict) | `seared` (lax) | `pydantic` | `seared+rusted` |
|------|---------------|-------------------|----------------|------------|-----------------|
| load | 8,395 ops/s   | 30,553 ops/s (~3.6×) | 30,588 ops/s (~3.6×) | 159,730 ops/s | 342,157 ops/s |
| dump | 25,849 ops/s  | 44,453 ops/s (~1.7×) | 50,551 ops/s (~2.0×) | 184,525 ops/s | 416,142 ops/s |

Per-op timing:

| Op   | `marshmallow` | `seared` (strict) | `seared` (lax) | `pydantic` | `seared+rusted` |
|------|---------------|-------------------|----------------|------------|-----------------|
| load | 119 µs        | 32.7 µs           | 32.7 µs        | 6.3 µs     | 2.9 µs          |
| dump | 39 µs         | 22.5 µs           | 19.8 µs        | 5.4 µs     | 2.4 µs          |

Ratios in the first table are versus `marshmallow`. Earlier recorded
baselines (e.g. the 2026-04-24 run against marshmallow 3.26, where seared
led load by ~8×) are in the git history of `bench/results.json`'s
predecessors; marshmallow 4 closed part of the gap.

Run-to-run spread on this hardware is roughly ±10%, so treat the ratios as
the durable claim and the absolute numbers as one sample.

## Reading the results

- **Versus marshmallow** (the like-for-like pure-Python comparison),
  seared loads ~3.6× and dumps ~1.7× faster.
- **Versus pydantic**, pure-Python seared is ~5× slower. That is the
  expected cost of pure Python versus a compiled Rust core, and it is the
  trade seared makes by default: zero runtime dependencies, no binary
  wheels.
- **With `rusted` installed that trade is optional rather than permanent.**
  The same classes run ~11× faster on `load` and ~9× on `dump` than the
  Python path, and ahead of pydantic on this schema — for a `uv add` and no
  code change. The default stays pure Python; every platform without a
  wheel keeps working.
- **Strict versus lax is within noise on `load`** (the guards are cheap
  `isinstance` checks against builtin types) but costs ~14% on `dump`,
  where those guards are most of what the pass actually does. `rusted`
  closes the load gap to nothing and leaves the dump gap at ~15% — cheaper
  guards, not absent ones. Most of seared's advantage over marshmallow comes
  from per-call overhead, not validation.

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

To include the `seared+rusted` rows, install the accelerator alongside:

```sh
uv pip install rusted        # or: uv pip install path/to/rusted-*.whl
uv run --no-sync python -m bench
```

Each recorded `Measurement` carries the version of what produced it —
`seared+rusted` rows read `0.3.0/rusted 0.1.2` — so a results file always
says which code the numbers came from.

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
  headline) from `bench/results.json` instead of hand-copying. Today the
  numbers in this file are transcribed by hand, which is the most likely
  way for a doc to drift from its own artifact.
