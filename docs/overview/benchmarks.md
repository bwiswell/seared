# Benchmarks

Throughput comparison against `marshmallow` on a representative nested
schema. Headline numbers also live on the [README](../../README.md);
this doc is the full methodology + reproduction guide.

## Schema

One outer object with a 20-item list of 3-field records plus a list of
3 string tags:

```python
@s.seared
class Inner(s.Seared):
    x: int = s.Int(required=True)
    y: float = s.Float(required=True)
    label: Optional[str] = s.Str()

@s.seared
class Outer(s.Seared):
    name: str = s.Str(required=True)
    items: list = s.T(Inner, many=True, required=True)
    tags: list = s.Str(many=True, missing=[])
```

```python
payload = {
    'name': 'demo',
    'items': [{'x': i, 'y': i * 1.5, 'label': f'i{i}'} for i in range(20)],
    'tags': ['alpha', 'beta', 'gamma'],
}
```

## Configurations

- **`marshmallow` 3.26** — equivalent schema using
  `Schema` + `Nested` + `List`. Runs the schema's `.load()` / `.dump()`
  in a tight loop. Apples-to-apples — same payload, same coercion
  behavior at the field level.
- **`seared` 0.2.0 (strict)** — default `@s.seared`, equivalent to
  `validate=True`. Type checks fire on every field per call.
- **`seared` 0.2.0 (lax)** — `@s.seared(validate=False)`. Skips type
  guards; coerces where obvious. Useful when inputs are already known-good
  (e.g. internal RPC, post-validation pipeline stages).

20,000 iterations per direction, single-threaded, time via
`time.perf_counter()`. Both benches run the same payload built once
upfront.

## Results

| Op   | `marshmallow` 3.26 | `seared` 0.2.0 (strict) | `seared` 0.2.0 (lax) |
|------|--------------------|-------------------------|----------------------|
| load | 4,743 ops/s        | 37,454 ops/s (~7.9×)    | 37,905 ops/s (~8.0×) |
| dump | 16,042 ops/s       | 42,338 ops/s (~2.6×)    | 48,988 ops/s (~3.1×) |

Per-op timing:

| Op   | `marshmallow` | `seared` (strict) | `seared` (lax) |
|------|---------------|-------------------|----------------|
| load | 211 µs        | 27 µs             | 26 µs          |
| dump | 62 µs         | 24 µs             | 20 µs          |

## Why seared is fast

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

The strict / lax difference is small (~1% on `load`, ~16% on `dump`)
because the type guards are cheap (`isinstance` checks against builtin
types). Most of the savings versus `marshmallow` come from the per-call
overhead, not validation.

## Reproduction

```sh
# 1. Install marshmallow ad-hoc — it is NOT a seared dependency.
uv pip install 'marshmallow>=3.26.1,<4.0'

# 2. Run both benches.
uv run python bench/bench_roundtrip.py    # seared (strict + lax)
uv run python bench/bench_marshmallow.py  # marshmallow
```

Both files print `ops/s` and `µs/op`. The numbers above are from a 2026
laptop-class CPU; relative ratios should hold across hardware.

## Caveats

- **Single-threaded, single-process.** No GIL contention, no shared-state
  serialisation overhead. Real-world throughput depends on what else the
  process is doing.
- **Static schema.** Both libraries cache schema introspection at class /
  decorator construction. Hot-path performance reflects the steady state;
  cold-start (importing seared, building the first decorated class) is
  not measured here.
- **No I/O.** The `dumps` / `loads` paths bottom out in `json.dumps` /
  `json.loads` from stdlib; the bench measures the pure transformation
  layer. JSON serialisation cost is identical between libraries.
- **Field type coverage matches marshmallow.** The bench schema sticks
  to `Int` / `Float` / `Str` / nested object / list-of-objects /
  list-of-strings — the field types both libraries handle natively. Fields
  exclusive to seared (`Decimal`, `Path`, `UUID`, `PandasFrame`,
  `PolarsFrame`, `NDArray`, tagged `Union`) aren't in the comparison
  because `marshmallow` doesn't ship equivalents; head-to-head wouldn't
  be meaningful.

## Future work

- **msgpack carrier benchmark.** `format='msgpack'` skips base64 for
  binary fields — significant on `Bytes`-heavy schemas.
- **DataFrame field benchmarks.** Records-form encode / decode versus
  Arrow IPC alternatives.
- **Cold-start measurements.** First-decoration cost matters for short-
  lived processes (e.g. CLI tools).
