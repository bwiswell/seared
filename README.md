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
- **Fast for pure Python.** <!-- bench:load-vs-marshmallow -->~3.7×<!-- /bench:load-vs-marshmallow --> faster `load` and <!-- bench:dump-vs-marshmallow -->~2.0×<!-- /bench:dump-vs-marshmallow --> faster `dump` than `marshmallow` on a representative nested schema (see [Benchmarks](#benchmarks)).
- **Optionally compiled.** Install [`rusted`](https://github.com/bwiswell/rusted) and the same classes run <!-- bench:rusted-load -->~11×<!-- /bench:rusted-load --> faster on `load`, <!-- bench:rusted-dump -->~8×<!-- /bench:rusted-dump --> on `dump` — no code change, and seared itself stays pure Python and zero-dependency (see [Accelerator](#accelerator)).
- **Compact.** `@s.seared` classes are `__slots__` dataclasses by default — lower memory per instance, faster attribute access.
- **One decorator, one base class.** No schema-class boilerplate; field types live as defaults on the dataclass.
- **Typed-callable fields.** `Bool`, `Bytes`, `Date`, `DateTime`, `Decimal`, `Dict`, `Enum`, `Float`, `Int`, `Path`, `Str`, `T`, `Time`, `TimeDelta`, `Tuple`, `Union`, `UUID`, plus optional `NDArray`, `PandasFrame`, `PolarsFrame`.
- **Tagged unions.** `s.Union(variants=…)` decodes `{tag, payload}` envelopes to typed variant instances; pattern-match at the dispatch site. Multiple Unions per class as long as their wire keys are disjoint.
- **Schema-evolution fallback.** `s.Union(fallback=Variant)` coerces unknown tags to a sentinel variant rather than raising — useful for older consumers receiving newer schemas.
- **File-format codecs out of the box.** `Cls.to_json` / `Cls.from_json` / `Cls.to_toml` / `Cls.from_toml` / `Cls.to_yaml` / `Cls.from_yaml` / `Cls.to_csv` / `Cls.from_csv` are auto-attached at decorator time. JSON / TOML-read / CSV are stdlib; YAML / TOML-write / DataFrame fields are optional extras.
- **`format=` carrier hint.** `Cls.dump(obj, format='msgpack')` threads the hint into each field; `Bytes` switches to native binary, dropping the ~33% base64 overhead, and `T` and `Tuple` pass the hint to what they hold.
- **Typed & type-checker-friendly.** `@s.seared` is a PEP 681 `@dataclass_transform`, so `x: str = s.Str(...)` type-checks under `ty` / `pyright` / `mypy` — no `invalid-assignment`, and `.load()` results carry their annotated attribute types. See [Type checking](#type-checking).
- **`null` is absent unless you say otherwise.** A wire `null` can't satisfy `required=True` or displace a default; `nullable=True` makes `None` a real value that `load` keeps and `dump` writes. See [`docs/fields/field.md`](docs/fields/field.md#null-on-the-wire).
- **Mutable-default safety.** `default_factory=list` / `default_factory=dict` / `default_factory=set` build a fresh value per-instance — no shared-default footgun. (A mutable `default=[...]` is deep-copied per-instance as a fallback.)
- **Path normalisation.** `s.Path` always serialises as POSIX strings; round-trip is cross-platform deterministic.
- **Lossless `Decimal`.** String-by-default wire form preserves every digit; opt into JSON-number form per field with `as_number=True`.
- **Introspection.** `Cls.__seared_fields__` exposes the field layout as a tuple of `s.FieldSpec(attr, wire, field)` named tuples for runtime tooling.

## Setup

Each release is tagged `v<version>` on GitHub (the first is `v0.3.4`; the latest is `v0.4.3`).
Install one by its tag:

```sh
# uv
uv add git+https://github.com/bwiswell/seared --tag v0.4.3

# pip
pip install git+https://github.com/bwiswell/seared.git@v0.4.3
```

`uv add` records the tag as the dependency's source:

```toml
[tool.uv.sources]
seared = { git = "https://github.com/bwiswell/seared", tag = "v0.4.3" }
```

**The tag is the pin.** uv doesn't check a version specifier such as
`seared>=0.4,<0.5` against a git source: it takes whatever the source points
at, and a source without a tag points at the tip of `master`. Moving to a new
release means moving the tag. What changed in each release, and what may
break on the way, is in [`CHANGELOG.md`](CHANGELOG.md).

Requires Python ≥ 3.14.

**Note:** if the consuming project uses `hatchling` as its build backend,
adding `seared` as a direct git reference may require enabling
`allow-direct-references` in that project's `pyproject.toml`:

```toml
[tool.hatch.metadata]
allow-direct-references = true
```

## Upgrading to 0.4.0

0.4.0 is seared's breaking release. Every break is listed here with what
to do; the full list is in [`CHANGELOG.md`](CHANGELOG.md).

**1. Error messages name their location.** A `ValidationError` reads
`Cls.path: reason`, as in `Outer.items[1].n: cannot deserialize 'x' as int`.
Match a pattern against `err.reason`, which keeps each field's text word for
word. Two messages are reworded: `Outer.n is required` reads
`Outer.n: required key missing` (naming the wire key), and
`Outer.load expected dict, got list` reads `Outer: expected dict, got list`.

**2. Install `rusted` 0.4.0 with it.** seared emits `SPEC_ABI` 2, so it
declines `rusted` 0.3.x: every class runs the pure-Python path, correct but
slower, and `SEARED_ACCEL=require` raises `SearedError` when a class is
decorated. Install rusted by its `v0.4.0` tag (see [Accelerator](#accelerator)).

**3. `Union(default=)` is `Union(fallback=)`.** On a `Union`, `default=`
(anything but `None`) and `default_factory=` raise `TypeError` pointing at
`fallback=`.

**4. `missing=` is gone.** Use `default=`, or `default_factory=` for a
mutable default. `Field.missing` goes with it; read `f.default`.

**5. A wire `null` reads as absent** on a field that isn't `nullable=True`:
a required field raises `required key missing`, and a defaulted one gets its
default, where the `null` used to satisfy `required` and replace the default
with `None`. seared's own `dump` never wrote those `null`s, so only `null`s
from elsewhere are affected. Declare `nullable=True` where `null` is a real
value (see [`field.md`](docs/fields/field.md#null-on-the-wire)).

**6. Strict coercion no longer loses data.** A strict `Int` refuses `3.7`,
which it truncated; a strict `Bool` refuses ints other than `0` and `1`; and
a strict int-valued `Enum` refuses `2.9` and `True`. Lax mode is unchanged.
Where such input loaded before, clean it, or declare the class
`validate=False`.

**7. `inf` into an `Int`, or an int-valued `Enum`, raises
`ValidationError`** in both modes, where it raised a bare `OverflowError`.

**8. Regenerate committed schema docs.** `seared.doc`'s fields table shows
`None` defaults where it showed `null`, notes nullable fields, and marks a
`Union` row required, so `--check` fails until a page is regenerated once
(see [Schema docs](#schema-docs)).

**9. CSV reads an empty cell as null**, by item 5's rule: a `Str` gets its
default (or `None` when nullable) where it got `''`, and an empty required
cell raises. `to_csv` heads each column with its wire key and gives a
`dump=False` field no column.

**10. msgpack writes a `Tuple`'s `Bytes` slot as raw bytes**, as it writes a
top-level `Bytes`, where it wrote base64. Payloads written before still load.

**11. Pins.** Move seared's source to a 0.4 tag (`v0.4.3` is the latest), and
`rusted` to its `v0.4.0` with it: 0.4.1 to 0.4.3 change nothing `rusted`
sees. zeared pins seared by tag itself (zeared 0.4.2 pins `v0.4.2`), and uv
refuses two tags for one package, so a project on both uses the seared tag
its zeared pins.

## Quick start

```python
from enum import Enum

import seared as s


class MyEnum(Enum):
    A = 0
    B = 1
    C = 2


@s.seared
class Inner(s.Seared):
    a: int | None   = s.Int(data_key='propertyA', default=None)
    b: float | None = s.Float(data_key='propertyB', default=None)
    c: str | None   = s.Str(data_key='propertyC', default=None)


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
@s.seared(accel=False)       # keep the pure-Python load/dump (default: accel=True)
@s.seared(unknown='raise')   # refuse keys the class doesn't declare (default: 'ignore')
```

The four options are orthogonal. `validate=True` (the default) raises
`s.ValidationError` on type mismatches during load/dump; `validate=False`
trusts the caller and is faster on hot paths where inputs are already
known-good. `accel=False` keeps the class off the compiled accelerator even
when `rusted` is installed (see [Accelerator](#accelerator)).
`unknown='raise'` is for config files (see
[Configuration files](#configuration-files)).

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
reveal_type(Cfg.load({'port': 7447}).name)  # str  (.load() returns the concrete class)
```

- Use **`default=`** (static) or **`default_factory=`** (per-instance,
  preferred for mutable values) to mark a field optional. These are the names
  the type checker reads to tell required from optional, so a field with
  neither — and without `required=True` — is treated as a required argument.
- The **annotation drives the attribute's type** (the stubs return `Any`), so
  `f: list[int] = s.Int(many=True, default_factory=list)` types as `list[int]`.
  The checker does not cross-check the annotation against the field kind;
  runtime validation still does.
- A **nullable** field is annotated `X | None`. `nullable` is independent of
  `required`, so `x: int | None = s.Int(nullable=True, required=True)` must
  be passed, but `None` is a legal value for it.

Because `seared` ships `py.typed`, downstream projects that previously excluded
their `@seared` modules from `ty` can drop those excludes.

## Tagged-union fields

`s.Union` encodes `{tag, payload}`-style envelopes and decodes to a typed
variant instance. Multiple `Union` fields per class are allowed as long as
their `tag_key` / `payload_key` strings don't collide. Set `fallback=Variant`
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

## Configuration files

`load` ignores a key its class doesn't declare. On the wire that's
load-bearing: an older subscriber reads a newer publisher's payload by
ignoring fields it doesn't know yet. In a config file it hides a typo,
since the misspelt key is dropped and its setting keeps its default.
`unknown='raise'` (0.4.1) refuses instead:

```python
@s.seared(unknown='raise')           # this class refuses wherever it's loaded
class Config(s.Seared):
    identity: str = s.Str(required=True)
    port: int = s.Int(default=7447)

Config.from_toml('identity = "a"\nprot = 8000\n')
# ValidationError: Config.prot: unknown key

Config.from_toml('identity = "a"\nprot = 8000\n', unknown='ignore')  # one call overrides the class
s.unknown_keys(Config, {'identity': 'a', 'prot': 8000})            # a report: [('prot',)]
```

The refusal covers nested sections, names every unknown key in one error,
and runs before the load, so a misspelt required key reads as unknown
rather than missing. It never touches the accelerator. Keep it off wire
messages. See [`docs/overview/configuration.md`](docs/overview/configuration.md)
and [`docs/_core/unknown.md`](docs/_core/unknown.md).

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
`s.FieldSpec` entries, one per declared field, in order. A `FieldSpec` is a
named tuple, so it unpacks as the `(attr, wire, field)` triple it has always
been, and it also reads by name:

```python
for attr, wire, field in Outer.__seared_fields__:
    ...

spec = Outer.__seared_fields__[0]
spec.attr, spec.wire, spec.field     # 'a', 'a', Int(...)
```

`s.field_kind(field)` says which built-in field a field is, as an
`s.FieldKind` (`FieldKind.INT`, `FieldKind.NESTED`, …), and a subclass of
`Str` is still `FieldKind.STR`. Map fields by kind rather than by
`type(field).__name__`, which misses a subclass. See
[`docs/fields/kind.md`](docs/fields/kind.md).

## Schema docs

`seared.doc` writes a Markdown page for every `@seared` class in a module or
package, from its fields, their `doc=` text and the class docstring, plus
an index. `--check` turns it into a CI guard that fails when the committed
pages have drifted from the code, and `--require-docs` (0.4.1) one that
fails when a field has no `doc=`.

```sh
seared-doc mypkg.models -o docs/models            # or: python -m seared.doc …
seared-doc mypkg.models -o docs/models --check    # exit 1 on drift
seared-doc mypkg.models -o docs/models --check --require-docs   # …or on a field without doc=
```

```python
page = s.document(Reading)      # one class → Markdown
model = s.introspect(Reading)   # the render-agnostic SchemaDoc behind it
```

Each page has a fields table (wire key, type, required, default, notes),
then the enum members and `Union` variants. Pages mirror the package tree
and link nested classes to each other. See
[`docs/doc/index.md`](docs/doc/index.md).

## JSON Schema

`seared.doc.json_schema` (0.4.2) describes a class's JSON wire form as a JSON
Schema 2020-12 document, for a tool's input and output, an API document, or a
check in another language. It describes and never validates, so seared
stays zero-dependency.

```python
from seared.doc import json_schema

json_schema(Reading)                    # the input: what load takes
json_schema(Reading, mode='dump')       # the output: what dump writes
json_schema(Reading, unknown='raise')   # closed: keys no class declares are refused
```

The two modes make two promises: input valid against the load schema
loads, and what `dump` writes validates against the dump schema. Nested
classes go under `$defs`, a `Union` is an envelope on its parent, and a
schema is closed exactly where `load` would refuse an unknown key, which by
default is where the class says (`@s.seared(unknown='raise')`).
`field_schema` gives one field's schema, for an object of your own. See
[`docs/doc/json_schema.md`](docs/doc/json_schema.md).

## Documentation

`docs/` mirrors the source layout exactly — namespace subdirs map to
namespace dirs in `docs/`, and each source file gets one `.md`.

- [`docs/overview/architecture.md`](docs/overview/architecture.md) — decorator pipeline, `UNWRAP`, format hints.
- [`docs/overview/benchmarks.md`](docs/overview/benchmarks.md) — full benchmark methodology, results, and reproduction steps.
- [`docs/seared.md`](docs/seared.md) — package re-export module entry point.
- [`docs/overview/configuration.md`](docs/overview/configuration.md) — seared for config files: refusing unknown keys, defaults, what it leaves to you.
- [`docs/_core/`](docs/_core/) — `Seared` base class, `@seared` decorator, exception hierarchy, the accelerator seam (`accel.md`), unknown keys (`unknown.md`).
- [`docs/fields/`](docs/fields/) — every Field subclass (one doc per file).
- [`docs/formats/index.md`](docs/formats/index.md) — file-format codecs (JSON / TOML / YAML / CSV).
- [`docs/doc/index.md`](docs/doc/index.md) — schema documentation generation (`seared.doc`), Markdown and JSON Schema.

## Errors

| Exception | Raised when |
|-----------|-------------|
| `s.ValidationError` | Wire value fails type checks; required field missing; bad enum member; unknown `Union` tag without `fallback=`; an unknown key, under `unknown='raise'`; CSV/Pandas/Polars shape mismatch. |
| `s.SearedError`     | Base; `ValidationError` extends this. Also extends `ValueError` for downstream compatibility (`except ValueError:` catches seared errors). Raised itself at decoration time for an unrecognised `SEARED_ACCEL`, or `SEARED_ACCEL=require` with no backend that loads. |

A `ValidationError` says where it happened. Its message reads
`Outer.items[1].n: cannot deserialize 'x' as int`, and the parts are
attributes: `.reason`, `.path` (on `load`, wire keys and indices into the
input you passed, so it retrieves the offending value) and `.cls_name`. See
[`docs/_core/errors.md`](docs/_core/errors.md) for the full hierarchy and the
path rules.

## Benchmarks

Nested schema (one outer object with a 20-item list of 3-field records plus
a list of strings) on an idle machine. Recorded
<!-- bench:run -->2026-10-17, Python 3.14.3, 20,000 iterations, median of 3 runs; seared 0.4.0, rusted 0.4.0, marshmallow 4.3.1, pydantic 2.14.1<!-- /bench:run -->;
ratios are versus marshmallow:

<!-- bench:ops -->
| Op   | `marshmallow` | `seared` (strict)    | `seared` (lax)       | `pydantic`    | `seared+rusted` |
|------|---------------|----------------------|----------------------|---------------|-----------------|
| load | 8,732 ops/s   | 32,413 ops/s (~3.7×) | 32,701 ops/s (~3.7×) | 151,905 ops/s | 354,951 ops/s   |
| dump | 24,887 ops/s  | 50,139 ops/s (~2.0×) | 55,743 ops/s (~2.2×) | 175,409 ops/s | 404,854 ops/s   |
<!-- /bench:ops -->

`seared (strict)` runs the default `validate=True`; `seared (lax)` is the
same schema decorated `@s.seared(validate=False)`. Both are benched with the
accelerator explicitly off, so these are the pure-Python numbers whatever
happens to be installed. Every number is
<!-- bench:runs -->the median of three runs<!-- /bench:runs -->, and every one in this
README is generated from the recorded results, prose included.
pydantic's compiled Rust core outruns pure Python — that is the trade seared
makes by default, and [`rusted`](#accelerator) is how you opt out of it
without changing a line of your own code.

The bench lives in [`bench/`](bench/)
(`uv sync --extra bench && uv run python -m bench --runs 3`) and records to
[`bench/results.json`](bench/results.json); methodology, run-to-run spread
and caveats are in [`docs/overview/benchmarks.md`](docs/overview/benchmarks.md).

## Accelerator

seared is pure Python and zero-dependency, and stays that way. When the
optional compiled core [`rusted`](https://github.com/bwiswell/rusted) is
installed, `@s.seared` swaps its generated `load` / `dump` for compiled
equivalents — same classes, same API, same error messages,
<!-- bench:rusted-load -->~11×<!-- /bench:rusted-load --> on `load` and
<!-- bench:rusted-dump -->~8×<!-- /bench:rusted-dump --> on `dump`.

```sh
uv add git+https://github.com/bwiswell/rusted --tag v0.4.0   # nothing in your code changes
```

(It isn't on a package index yet, so that git form builds from source and
needs a Rust toolchain. A prebuilt wheel is the intent; until then the
accelerator is developer-only.)

seared and its backend agree through one integer, `SPEC_ABI`, which is 2 from
seared 0.4.0. `rusted` 0.4.0 is the matching release. An older `rusted` still
loads, but it declares `SPEC_ABI` 1, so every class declines it and keeps the
Python path: correct, just not accelerated.

Acceleration is **per class, all or nothing**: a class qualifies only if
every field, recursively through `T`, is a seared-native type the backend
implements — today that is everything except `Tuple`, `Union`, and the
`NDArray` / DataFrame fields. Classes with a hand-written `__init__`, a
`__post_init__`, or a plain dataclass attribute that isn't a seared field
(`b: int = 5`) are also declined, since a compiled core builds instances
through `__new__` and only `__init__` would ever set those.

Anything unexpected — no wheel for your platform, a version mismatch, a
field the backend doesn't know — falls back to the Python path rather than
failing. So ask, rather than assume:

```python
>>> s.accel_status()          # did a backend load at all?
{'mode': 'auto', 'spec_abi': 2, 'available': True, 'backend': 'rusted', ...}

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

## Limits

- **JSON-by-default wire format** via `dumps` / `loads`. Binary carriers (msgpack, etc.) opt in via `Cls.dump(obj, format='msgpack')` — `Bytes` honours the hint, and `T` and `Tuple` pass it on; other fields are unaffected.
- **No async variants.** seared is pure CPU-bound transformation; no async path is planned.
- **`nullable` is about a field's own value.** A `null` *element* inside a `many` / `keyed` collection is an error in strict mode (lax mode coerces it per kind; see [`field.md`](docs/fields/field.md#null-on-the-wire)), and a `Union` can't be nullable. TOML has no null, so `to_toml` leaves a nullable `None` out and it reads back as absent.
- **Construction doesn't check `required`.** `Cls()` without a required field builds an instance holding `None` there. The type checker flags the call; only `load` raises.
- **Unknown wire keys are ignored** on `load`, by design: an older consumer can read a newer producer's payload.
- **Strict mode still coerces, without losing data.** `Int` reads numeric strings (`'42'`) and integral floats (`3.0`), but refuses `3.7`, which lax mode truncates; `Bool` reads `'yes'` / `'off'` and the ints `0` / `1`; `Float` reads `'nan'`. String coercion is deliberate, since it is how string-only sources such as topic-key captures decode.
- **NaN dumps as bare `NaN`**, which is Python's `json` default but not standard JSON. Pass `allow_nan=False` to `Cls.dumps` or `Cls.to_json` to refuse it, as JSON bound for a browser should.
- **Mutable defaults** are per-instance: `default_factory=callable` builds a fresh value each time (preferred); a mutable `default=[...]` is deep-copied per-instance as a fallback.
- **CSV is flat-only.** Nested fields and `many=True` / `keyed=True` collections raise `TypeError` at call time. Flatten-and-rehydrate is deferred to a future release.
- **DataFrame fields are records-form only.** Dtype-preserving transport (Parquet / Arrow IPC) is out of scope.

## Development

```sh
uv sync
uv run pytest tests/
```

Hooks run through `prek`; install them once per clone with
`uv run prek install`. Four check every commit that touches Python:

```sh
uv run ruff check     # lint
uv run ruff format    # format
uv run deptry .       # dependency hygiene
uv run ty check       # type check
```

A fifth, `uv run python -m bench.tables --check`, runs whenever the README,
`docs/overview/benchmarks.md` or `bench/` changes. Every benchmark number in
those two docs is generated from `bench/results.json`, and the check fails
when one has drifted from it; recording a run re-renders them (see
[`docs/overview/benchmarks.md`](docs/overview/benchmarks.md#reproduction)).
A sixth refuses any commit on `master`.

**Branches and releases.**
- **`master` holds released commits only,** and moves only by merge.
- **A release is a `version/x.y.z` branch** off `master`.
- **Work on it happens in `feat/…` and `fix/…` branches,** each a pull
  request squash-merged into the version branch.
- **Once those are all in, a `chore/version-bump-and-benches` branch** makes
  two commits:
  1. it bumps the version, in `pyproject.toml` and `seared/__init__.py`
     together (a test checks that they agree);
  2. it re-records the benchmarks.
- **The version branch then merges into `master`.** There, the `Release Tag`
  workflow (`.github/workflows/release-tag.yml`) tags it `v<version>` and
  publishes a GitHub release.

Tests mirror the source layout exactly — one `test_*.py` per source file,
including subdir structure (`tests/_core/`, `tests/doc/`, `tests/fields/`, `tests/formats/`).
