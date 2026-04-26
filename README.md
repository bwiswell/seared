# seared

`seared` is a lightweight, dependency-free serialization library for Python.
Declare typed `__slots__` dataclasses and get `load` / `dump` / `loads` /
`dumps` plus per-format file codecs (`to_json` / `from_json` / `to_toml` / …)
for free.

> Looking for typed Zenoh pub/sub on top of seared? See its sister package
> [`zeared`](https://www.github.com/bwiswell/zeared). Its public surface
> re-exports every seared field type, so `import zeared as z` is enough for
> most use cases.

## Why seared

- **Zero runtime dependencies.** Pure stdlib core. Numpy / pandas / polars / PyYAML / tomli-w live behind opt-in extras.
- **Fast.** ~8× faster `load` and ~2.6–3.1× faster `dump` than `marshmallow` on a representative nested schema (see [Benchmarks](#benchmarks)).
- **Compact.** `@s.seared` classes are `__slots__` dataclasses by default — lower memory per instance, faster attribute access.
- **One decorator, one base class.** No schema-class boilerplate; field types live as defaults on the dataclass.
- **Typed-callable fields.** `Bool`, `Bytes`, `Date`, `DateTime`, `Decimal`, `Dict`, `Enum`, `Float`, `Int`, `Path`, `Str`, `T`, `Time`, `TimeDelta`, `Tuple`, `Union`, `UUID`, plus optional `NDArray`, `PandasFrame`, `PolarsFrame`.
- **Tagged unions.** `s.Union(variants=…)` decodes `{tag, payload}` envelopes to typed variant instances; pattern-match at the dispatch site. Multiple Unions per class as long as their wire keys are disjoint.
- **Schema-evolution fallback.** `s.Union(default=Variant)` coerces unknown tags to a sentinel variant rather than raising — useful for older consumers receiving newer schemas.
- **File-format codecs out of the box.** `Cls.to_json` / `Cls.from_json` / `Cls.to_toml` / `Cls.from_toml` / `Cls.to_yaml` / `Cls.from_yaml` / `Cls.to_csv` / `Cls.from_csv` are auto-attached at decorator time. JSON / TOML-read / CSV are stdlib; YAML / TOML-write / DataFrame fields are optional extras.
- **`format=` carrier hint.** `Cls.dump(obj, format='msgpack')` threads the hint into each field; `Bytes` and `NDArray` switch to native binary, dropping the ~33% base64 overhead.
- **Mutable-default safety.** `missing=[]` / `missing={}` / `missing=set()` deep-copies per-instance — no shared-default footgun at the dataclass layer.
- **Path normalisation.** `s.Path` always serialises as POSIX strings; round-trip is cross-platform deterministic.
- **Lossless `Decimal`.** String-by-default wire form preserves every digit; opt into JSON-number form per field with `as_number=True`.
- **Introspection.** `Cls.__seared_fields__` exposes the field layout as a tuple of `(attr, wire_key, Field)` for runtime tooling.

## Setup

```sh
# pip
pip install git+https://www.github.com/bwiswell/seared.git

# uv
uv add git+https://www.github.com/bwiswell/seared.git
```

Requires Python ≥ 3.11.

**Note:** if the consuming project uses `hatchling` as its build backend,
adding `seared` as a direct git reference may require enabling
`allow-direct-references` in that project's `pyproject.toml`:

```toml
[tool.hatch.metadata]
allow-direct-references = true
```

## Quick start

```python
from enum import Enum
from typing import Optional

import seared as s


class MyEnum(Enum):
    A = 0
    B = 1
    C = 2


@s.seared
class Inner(s.Seared):
    a: Optional[int]   = s.Int(data_key='propertyA')
    b: Optional[float] = s.Float(data_key='propertyB')
    c: Optional[str]   = s.Str(data_key='propertyC')


@s.seared
class Outer(s.Seared):
    a: int               = s.Int(missing=5)
    b: float             = s.Float(missing=3.14)
    c: str               = s.Str(missing='hello')
    d: Inner             = s.T(Inner, required=True)
    e: MyEnum            = s.Enum(enum=MyEnum, missing=MyEnum.B)
    f: list[int]         = s.Int(many=True, missing=[])
    g: dict[str, float]  = s.Float(keyed=True, missing={})


data = {
    'a': 3, 'c': 'world',
    'd': {'propertyA': 5},
    'e': 2,
    'f': [3, 7, 4, 1],
    'g': {'a': 3.5, 'b': 1.6},
}

obj  = Outer.load(data)        # dict → typed instance
raw  = Outer.dumps(obj)        # typed instance → JSON str
obj2 = Outer.loads(raw)        # JSON str → typed instance

# Or via the per-format codec methods:
text = Outer.to_yaml(obj)      # requires seared[yaml]
also = Outer.from_json(raw)
```

## Decorator options

```python
@s.seared(slots=False)       # allow instance __dict__ (default: slots=True)
@s.seared(validate=False)    # lax mode: skip type checks, coerce where obvious
```

Both flags are orthogonal. `validate=True` (the default) raises
`s.ValidationError` on type mismatches during load/dump; `validate=False`
trusts the caller and is faster on hot paths where inputs are already
known-good.

See [`docs/_core/decorator.md`](docs/_core/decorator.md) for the full
internals.

## Tagged-union fields

`s.Union` encodes `{tag, payload}`-style envelopes and decodes to a typed
variant instance. Multiple `Union` fields per class are allowed as long as
their `tag_key` / `payload_key` strings don't collide. Set `default=Variant`
to coerce unknown tags to a sentinel variant rather than raising. Full
details — flat vs. nested envelopes, schema-evolution fallback,
disjoint-key validation — in [`docs/fields/union.md`](docs/fields/union.md).

## File-format codecs

Every `@s.seared` class gets per-format `to_*` / `from_*` classmethods
auto-attached at decorator time:

```python
@s.seared
class Cfg(s.Seared):
    name: str = s.Str(required=True)
    port: int = s.Int(required=True)

cfg = Cfg(name='alpha', port=7447)

Cfg.to_json(cfg)                      # → '{"name": "alpha", "port": 7447}'
Cfg.to_toml(cfg)                      # → 'name = "alpha"\nport = 7447\n'
Cfg.to_yaml(cfg)                      # → 'name: alpha\nport: 7447\n'

Cfg.from_json('config.json')          # ← path or string content
Cfg.from_toml(toml_text)
Cfg.from_yaml(yaml_text)

# CSV is class-method-only (a CSV file is a list of records):
rows = [Cfg(name='a', port=1), Cfg(name='b', port=2)]
text = Cfg.to_csv(rows)
loaded = Cfg.from_csv(text)           # ← list[Cfg]
```

Stdlib formats (JSON, TOML-read, CSV) work out of the box. Optional
formats live behind extras:

| Extra | Adds |
|-------|------|
| `seared[yaml]` | `to_yaml` / `from_yaml` (PyYAML) |
| `seared[toml]` | `to_toml` write (read uses stdlib `tomllib`) |
| `seared[numpy]` | `s.NDArray` field |
| `seared[pandas]` | `s.PandasFrame` field |
| `seared[polars]` | `s.PolarsFrame` field |
| `seared[all]` | every optional dep |

CSV refuses nested fields (`T`, `Union`, `NDArray`, `Tuple`,
`PandasFrame`, `PolarsFrame`) and `many=True` / `keyed=True` — flat
classes only. See [`docs/formats/index.md`](docs/formats/index.md) for
the full codec matrix.

## DataFrame fields

```python
import pandas as pd
import seared as s

@s.seared
class Report(s.Seared):
    name: str          = s.Str(required=True)
    data: pd.DataFrame = s.PandasFrame(required=True)

r = Report(name='r1', data=pd.DataFrame({'a': [1, 2], 'b': [3, 4]}))
encoded = Report.to_json(r)
loaded  = Report.from_json(encoded)
loaded.data.equals(r.data)            # → True
```

`s.PolarsFrame` is the same shape with polars in place of pandas. Wire
form is JSON-records (`[{col: val, ...}, ...]`); dtype-preserving wire
transport (Parquet / Arrow IPC) is out of scope. See
[`docs/fields/pandas_.md`](docs/fields/pandas_.md) and
[`docs/fields/polars_.md`](docs/fields/polars_.md).

## Introspection

Every `@s.seared` class exposes its field layout as a tuple of
`(attr_name, wire_key, Field)`:

```python
for attr, wire, field in Outer.__seared_fields__:
    ...
```

## Documentation

`docs/` mirrors the source layout exactly — namespace subdirs map to
namespace dirs in `docs/`, and each source file gets one `.md`.

- [`docs/overview/architecture.md`](docs/overview/architecture.md) — decorator pipeline, `UNWRAP`, format hints.
- [`docs/overview/benchmarks.md`](docs/overview/benchmarks.md) — full benchmark methodology, results, and reproduction steps.
- [`docs/seared.md`](docs/seared.md) — package re-export module entry point.
- [`docs/_core/`](docs/_core/) — `Seared` base class, `@seared` decorator, exception hierarchy.
- [`docs/fields/`](docs/fields/) — every Field subclass (one doc per file).
- [`docs/formats/index.md`](docs/formats/index.md) — file-format codecs (JSON / TOML / YAML / CSV).

## Errors

| Exception | Raised when |
|-----------|-------------|
| `s.ValidationError` | Wire value fails type checks; required field missing; bad enum member; unknown `Union` tag without `default=`; CSV/Pandas/Polars shape mismatch. |
| `s.SearedError`     | Base; `ValidationError` extends this. Also extends `ValueError` for downstream compatibility (`except ValueError:` catches seared errors). |

See [`docs/_core/errors.md`](docs/_core/errors.md) for the full hierarchy.

## Benchmarks

Nested schema (one outer object with a 20-item list of 3-field records plus
a list of strings), 20k iterations:

| Op   | `marshmallow` 3.26 | `seared` 0.2.0 (strict) | `seared` 0.2.0 (lax) |
|------|--------------------|-------------------------|----------------------|
| load | 4,743 ops/s        | 37,454 ops/s (~7.9×)    | 37,905 ops/s (~8.0×) |
| dump | 16,042 ops/s       | 42,338 ops/s (~2.6×)    | 48,988 ops/s (~3.1×) |

`seared (strict)` runs the default `validate=True`; `seared (lax)` is the
same schema decorated `@s.seared(validate=False)`. Reproduction steps and
caveats in [`docs/overview/benchmarks.md`](docs/overview/benchmarks.md).

## Limits (v0.2.0)

- **JSON-by-default wire format** via `dumps` / `loads`. Binary carriers (msgpack, etc.) opt in via `Cls.dump(obj, format='msgpack')` — `Bytes` and `NDArray` honour the hint; other fields are unaffected.
- **No nullable-true fields** — `None` is always stripped from dumps; explicit JSON `null` is not emittable.
- **No async variants.** seared is pure CPU-bound transformation; no async path is planned.
- **Mutable `missing` values** (`list` / `dict` / `set` / `frozenset`) are deep-copied per-instance. For per-instance computed defaults, use a factory pattern in user code (a `missing_factory=callable` kwarg is on the backlog).
- **CSV is flat-only.** Nested fields and `many=True` / `keyed=True` collections raise `TypeError` at call time. Flatten-and-rehydrate is deferred to a future release.
- **DataFrame fields are records-form only.** Dtype-preserving transport (Parquet / Arrow IPC) is out of scope.

## Development

```sh
uv sync
uv run pytest tests/
```

Tests mirror the source layout exactly — one `test_*.py` per source file,
including subdir structure (`tests/_core/`, `tests/fields/`, `tests/formats/`).
