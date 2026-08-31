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
- **Fast for pure Python.** ~3.6× faster `load` and ~1.7× faster `dump` than `marshmallow` on a representative nested schema (see [Benchmarks](#benchmarks)).
- **Optionally compiled.** Install [`rusted`](https://github.com/bwiswell/rusted) and the same classes run ~11× faster on `load`, ~9× on `dump` — no code change, and seared itself stays pure Python and zero-dependency (see [Accelerator](#accelerator)).
- **Compact.** `@s.seared` classes are `__slots__` dataclasses by default — lower memory per instance, faster attribute access.
- **One decorator, one base class.** No schema-class boilerplate; field types live as defaults on the dataclass.
- **Typed-callable fields.** `Bool`, `Bytes`, `Date`, `DateTime`, `Decimal`, `Dict`, `Enum`, `Float`, `Int`, `Path`, `Str`, `T`, `Time`, `TimeDelta`, `Tuple`, `Union`, `UUID`, plus optional `NDArray`, `PandasFrame`, `PolarsFrame`.
- **Tagged unions.** `s.Union(variants=…)` decodes `{tag, payload}` envelopes to typed variant instances; pattern-match at the dispatch site. Multiple Unions per class as long as their wire keys are disjoint.
- **Schema-evolution fallback.** `s.Union(default=Variant)` coerces unknown tags to a sentinel variant rather than raising — useful for older consumers receiving newer schemas.
- **File-format codecs out of the box.** `Cls.to_json` / `Cls.from_json` / `Cls.to_toml` / `Cls.from_toml` / `Cls.to_yaml` / `Cls.from_yaml` / `Cls.to_csv` / `Cls.from_csv` are auto-attached at decorator time. JSON / TOML-read / CSV are stdlib; YAML / TOML-write / DataFrame fields are optional extras.
- **`format=` carrier hint.** `Cls.dump(obj, format='msgpack')` threads the hint into each field; `Bytes` and `NDArray` switch to native binary, dropping the ~33% base64 overhead.
- **Typed & type-checker-friendly.** `@s.seared` is a PEP 681 `@dataclass_transform`, so `x: str = s.Str(...)` type-checks under `ty` / `pyright` / `mypy` — no `invalid-assignment`, and `.load()` results carry their annotated attribute types. See [Type checking](#type-checking).
- **Mutable-default safety.** `default_factory=list` / `default_factory=dict` / `default_factory=set` build a fresh value per-instance — no shared-default footgun. (A mutable `default=[...]` is deep-copied per-instance as a fallback.)
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

Requires Python ≥ 3.14.

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
    a: int               = s.Int(default=5)
    b: float             = s.Float(default=3.14)
    c: str               = s.Str(default='hello')
    d: Inner             = s.T(Inner, required=True)
    e: MyEnum            = s.Enum(enum=MyEnum, default=MyEnum.B)
    f: list[int]         = s.Int(many=True, default_factory=list)
    g: dict[str, float]  = s.Float(keyed=True, default_factory=dict)


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

## Type checking

`@s.seared` is marked as a [PEP 681](https://peps.python.org/pep-0681/)
`@dataclass_transform`, and each field constructor ships a `.pyi` stub, so the
declaration idiom checks cleanly under `ty`, `pyright`, and `mypy`:

```python
@s.seared
class Cfg(s.Seared):
    name: str = s.Str(default='alpha')   # no `invalid-assignment`
    port: int = s.Int(required=True)

cfg = Cfg(port=7447)     # `name` optional, `port` required — enforced
reveal_type(cfg.port)    # int
reveal_type(Cfg.load({}).name)  # str  (.load() returns the concrete class)
```

- Use **`default=`** (static) or **`default_factory=`** (per-instance,
  preferred for mutable values) to mark a field optional. These are the names
  the type checker reads to tell required from optional, so a field with
  neither — and without `required=True` — is treated as a required argument.
- **`missing=` is deprecated** — it still works at runtime (as an alias for
  `default=`) but emits a `DeprecationWarning` and is invisible to the type
  checker's required/optional inference.
- The **annotation drives the attribute's type** (the stubs return `Any`), so
  `f: list[int] = s.Int(many=True, default_factory=list)` types as `list[int]`.
  The checker does not cross-check the annotation against the field kind;
  runtime validation still does.

Because `seared` ships `py.typed`, downstream projects that previously excluded
their `@seared` modules from `ty` can drop those excludes.

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
a list of strings), 20k iterations. seared 0.3.0, rusted 0.1.2,
marshmallow 4.3.1, pydantic 2.13.5; ratios are versus marshmallow:

| Op   | `marshmallow` | `seared` (strict) | `seared` (lax) | `pydantic` v2 | `seared`+`rusted` |
|------|---------------|-------------------|----------------|---------------|-------------------|
| load | 8,395 ops/s   | 30,553 ops/s (~3.6×) | 30,588 ops/s (~3.6×) | 159,730 ops/s | 342,157 ops/s |
| dump | 25,849 ops/s  | 44,453 ops/s (~1.7×) | 50,551 ops/s (~2.0×) | 184,525 ops/s | 416,142 ops/s |

`seared (strict)` runs the default `validate=True`; `seared (lax)` is the
same schema decorated `@s.seared(validate=False)`. Both are benched with the
accelerator explicitly off, so these are the pure-Python numbers whatever
happens to be installed. pydantic's compiled Rust core outruns pure Python —
that is the trade seared makes by default, and [`rusted`](#accelerator) is
how you opt out of it without changing a line of your own code.

The bench lives in [`bench/`](bench/)
(`uv sync --extra bench && uv run python -m bench`) and records each run to
[`bench/results.json`](bench/results.json); methodology and caveats in
[`docs/overview/benchmarks.md`](docs/overview/benchmarks.md).

## Accelerator

seared is pure Python and zero-dependency, and stays that way. When the
optional compiled core [`rusted`](https://github.com/bwiswell/rusted) is
installed, `@s.seared` swaps its generated `load` / `dump` for compiled
equivalents — same classes, same API, same error messages, ~11× / ~9×.

```sh
uv add git+https://www.github.com/bwiswell/rusted.git   # nothing in your code changes
```

(It isn't on a package index yet, so that git form builds from source and
needs a Rust toolchain. A prebuilt wheel is the intent; until then the
accelerator is developer-only.)

Acceleration is **per class, all or nothing**: a class qualifies only if
every field, recursively through `T`, is a seared-native type the backend
implements — today that is everything except `Tuple`, `Union`, and the
`NDArray` / DataFrame fields. Classes with a hand-written `__init__` or a
`__post_init__` are also declined, since a compiled core builds instances
through `__new__`.

Anything unexpected — no wheel for your platform, a version mismatch, a
field the backend doesn't know — falls back to the Python path rather than
failing. So ask, rather than assume:

```python
>>> s.accel_status()          # did a backend load at all?
{'mode': 'auto', 'spec_abi': 1, 'available': True, 'backend': 'rusted', ...}

>>> Telemetry.__seared_accel__   # and did *this* class qualify?
AccelInfo(accelerated=True, backend='rusted', reason=None)

>>> HasTuple.__seared_accel__
AccelInfo(accelerated=False, backend=None,
          reason='HasTuple.pair: Tuple is not an accelerated field type')
```

Opt out per class with `@s.seared(accel=False)`, or globally with
`SEARED_ACCEL=off`. `SEARED_ACCEL=require` raises instead of falling back —
for CI that needs to assert the wheel is actually engaged. Full details in
[`docs/_core/accel.md`](docs/_core/accel.md).

## Limits (v0.3.0)

- **JSON-by-default wire format** via `dumps` / `loads`. Binary carriers (msgpack, etc.) opt in via `Cls.dump(obj, format='msgpack')` — `Bytes` and `NDArray` honour the hint; other fields are unaffected.
- **No nullable-true fields** — `None` is always stripped from dumps; explicit JSON `null` is not emittable.
- **No async variants.** seared is pure CPU-bound transformation; no async path is planned.
- **`missing=` is deprecated** in favour of `default=` / `default_factory=` (see [Type checking](#type-checking)). It remains a runtime alias for `default=` but warns and is invisible to type checkers.
- **Mutable defaults** are per-instance: `default_factory=callable` builds a fresh value each time (preferred); a mutable `default=[...]` is deep-copied per-instance as a fallback.
- **CSV is flat-only.** Nested fields and `many=True` / `keyed=True` collections raise `TypeError` at call time. Flatten-and-rehydrate is deferred to a future release.
- **DataFrame fields are records-form only.** Dtype-preserving transport (Parquet / Arrow IPC) is out of scope.

## Development

```sh
uv sync
uv run pytest tests/
```

Tests mirror the source layout exactly — one `test_*.py` per source file,
including subdir structure (`tests/_core/`, `tests/fields/`, `tests/formats/`).
