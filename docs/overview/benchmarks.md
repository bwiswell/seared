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
payload built once upfront. With `--runs N`, every case is timed N times,
the runs interleaved across the cases so that machine drift doesn't land on
one of them, and every number below is the median of the runs. The
committed results use three.

**The `seared` cases are pinned `accel=False`.** Otherwise an accelerator
wheel that happened to be installed in the benching environment would
silently retarget them, and compiled numbers would be recorded under
seared's own name. The accelerated path is measured only by
`seared+rusted`, which in turn asserts the seam actually engaged before
contributing a case — `import rusted` succeeding is not the same as a class
being accelerated.

## Results

Recorded <!-- bench:run -->2026-10-20, Python 3.14.3, 20,000 iterations, median of 3 runs; seared 0.4.4, rusted 0.4.0, marshmallow 4.3.1, pydantic 2.14.1<!-- /bench:run --> —
Linux x86_64 (WSL2), laptop-class CPU, otherwise idle. Raw numbers:
[`bench/results.json`](../../bench/results.json). The tables, and every
number quoted in the prose below, are rendered from that file
(`uv run python -m bench.tables`), never typed in.

<!-- bench:ops -->
| Op   | `marshmallow` | `seared` (strict)    | `seared` (lax)       | `pydantic`    | `seared+rusted` |
|------|---------------|----------------------|----------------------|---------------|-----------------|
| load | 8,830 ops/s   | 34,976 ops/s (~4.0×) | 35,392 ops/s (~4.0×) | 150,013 ops/s | 338,343 ops/s   |
| dump | 25,236 ops/s  | 56,092 ops/s (~2.2×) | 55,807 ops/s (~2.2×) | 173,354 ops/s | 406,967 ops/s   |
<!-- /bench:ops -->

Per-op timing:

<!-- bench:us -->
| Op   | `marshmallow` | `seared` (strict) | `seared` (lax) | `pydantic` | `seared+rusted` |
|------|---------------|-------------------|----------------|------------|-----------------|
| load | 113.3 µs      | 28.6 µs           | 28.3 µs        | 6.7 µs     | 3.0 µs          |
| dump | 39.6 µs       | 17.8 µs           | 17.9 µs        | 5.8 µs     | 2.5 µs          |
<!-- /bench:us -->

Ratios in the first table are versus `marshmallow`. Earlier recorded
baselines (e.g. the 2026-04-24 run against marshmallow 3.26, where seared
led load by ~8×) are in the git history of `bench/results.json`'s
predecessors; marshmallow 4 closed part of the gap.

### Run-to-run spread

Every number here is <!-- bench:runs -->the median of three runs<!-- /bench:runs -->.
How far each column's rate moved between the runs, as `max / min - 1`:

<!-- bench:spread -->
| Op   | `marshmallow` | `seared` (strict) | `seared` (lax) | `pydantic` | `seared+rusted` |
|------|---------------|-------------------|----------------|------------|-----------------|
| load | 4.8%          | 1.3%              | 0.4%           | 3.4%       | 2.0%            |
| dump | 2.6%          | 4.0%              | 0.4%           | 1.6%       | 2.4%            |
<!-- /bench:spread -->

The widest is <!-- bench:spread-max -->~5%<!-- /bench:spread-max -->.
Background load widens the spread, and the *ratios* move with it, so bench
on a quiet box and read the ratios as approximate: seared is
<!-- bench:load-vs-marshmallow -->~4.0×<!-- /bench:load-vs-marshmallow -->
marshmallow on load and
<!-- bench:dump-vs-marshmallow -->~2.2×<!-- /bench:dump-vs-marshmallow -->
on dump, and `rusted` is
<!-- bench:rusted-load -->~10×<!-- /bench:rusted-load --> /
<!-- bench:rusted-dump -->~7×<!-- /bench:rusted-dump --> over pure Python.

## Reading the results

- **Versus marshmallow** (the like-for-like pure-Python comparison),
  seared loads <!-- bench:load-vs-marshmallow -->~4.0×<!-- /bench:load-vs-marshmallow -->
  and dumps <!-- bench:dump-vs-marshmallow -->~2.2×<!-- /bench:dump-vs-marshmallow -->
  faster.
- **Versus pydantic**, pure-Python seared loads
  <!-- bench:pydantic-vs-seared -->~4.3×<!-- /bench:pydantic-vs-seared -->
  slower. That is the expected cost of pure Python versus a compiled Rust
  core, and it is the trade seared makes by default: zero runtime
  dependencies, no binary wheels.
- **With `rusted` installed that trade is optional rather than permanent.**
  The same classes run
  <!-- bench:rusted-load -->~10×<!-- /bench:rusted-load --> faster on `load`
  and <!-- bench:rusted-dump -->~7×<!-- /bench:rusted-dump --> on `dump`
  than the Python path, and load
  <!-- bench:rusted-vs-pydantic -->~2.3×<!-- /bench:rusted-vs-pydantic -->
  as fast as pydantic on this schema, for an install and no code change.
  The default stays pure Python; every platform without a wheel keeps
  working.
- **Strict versus lax is within noise, on `load` and on `dump`**: the two
  columns sit closer together than either moves between runs (see the
  spread table). The guards are cheap `isinstance` checks against builtin
  types, and since 0.4.4 an exact `int`, `float` or `str` on a field with no
  constraints skips them, which was most of what a strict `dump` checked.
  `rusted` matches the two on `load` and keeps a dump gap of
  <!-- bench:rusted-lax-dump-gain -->~16%<!-- /bench:rusted-lax-dump-gain -->,
  lax over strict: cheaper guards, not absent ones. Most of seared's
  advantage over marshmallow comes from per-call overhead, not validation.

## Why seared is fast (for pure Python)

- **`__slots__` everywhere.** No `__dict__` per instance; attribute access
  is a slot read.
- **No schema class layer.** Field metadata is stored as `Field` defaults
  on the dataclass; no separate `Schema` object indirection on every call.
- **Pre-baked spec tuple.** The loop spec is computed once at decorator
  time: `dump` / `load` walk plain `(attr, wire, field, unwrap)` tuples,
  with each field's `UNWRAP` flag already resolved, rather than the
  `FieldSpec` named tuples `__seared_fields__` exposes or a per-call
  `UNWRAP` check.
- **No Marshmallow `Meta` / `pre_load` / `post_dump` machinery.** The
  decorator does one simple pass per direction.
- **`format=` kwarg threading is free.** `Bytes` gets its carrier hint
  via `**kwargs` (`T` and `Tuple` pass it on); other fields ignore it — no
  per-call dispatch overhead.

## Reproduction

```sh
# From the repo root. Comparators are behind the `bench` extra —
# they are NOT seared dependencies.
uv sync --extra bench
uv run python -m bench --runs 3     # how the committed results are recorded
```

The runner prints an `ops/s` line per case and op, rewrites
`bench/results.json`, and re-renders every generated number in this file and
the README from it (suppress both with `--no-write`; tune with `-n` and
`--runs`; a scratch `--out` path records without touching the docs). To
re-render without re-running, or to check that the docs still match the
committed results:

```sh
uv run python -m bench.tables           # rewrite the numbers from results.json
uv run python -m bench.tables --check   # exit 1 if a doc has drifted
```

The check also runs as the `bench-tables` prek hook whenever the README,
this page or `bench/` changes. Missing comparators are skipped with a note,
so `uv run python -m bench` also works in a plain dev sync and times seared
alone. Absolute numbers vary by machine; relative ratios should hold across
hardware.

To include the `seared+rusted` rows, install the accelerator alongside. It
isn't on a package index, so install a wheel built from
[`rusted`](https://github.com/bwiswell/rusted), **after** any `uv sync`: a
sync is exact, and removes a package the lockfile doesn't name (`uv run`
leaves it alone).

```sh
uv pip install path/to/rusted-*.whl
uv run --no-sync python -m bench --runs 3
```

Each recorded `Measurement` carries the version of what produced it and the
run it came from (`seared+rusted` rows read
<!-- bench:version-example -->`0.4.4/rusted 0.4.0`<!-- /bench:version-example -->),
so a results file always says which code the numbers came from.

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
