# `_core/accel.py` — the optional-accelerator seam

seared's Python implementation is canonical and always present. When an
accelerator backend is installed, `@seared` swaps its generated `load` /
`dump` closures for the backend's compiled equivalents. When it isn't —
the default — nothing changes and nothing is paid.

[`rusted`](https://github.com/bwiswell/rusted) is the compiled backend
(Rust/PyO3). It is an **extra, never a dependency**: seared stays
zero-dependency and pure Python, and any platform without a wheel simply
runs the Python path.

```sh
uv add git+https://www.github.com/bwiswell/rusted.git   # nothing in your code changes
```

There is no `seared[core]` extra: seared declares no dependency on the
backend in either direction, so the accelerator is installed alongside
seared rather than through it. That is what keeps a missing or broken wheel
from being seared's problem.

## The four rules

1. **seared owns the knowledge of seared.** This module walks
   `__seared_fields__` and emits a **plain-data spec**; a backend never
   introspects a `Field`. The spec shape is versioned by `SPEC_ABI`, and a
   backend declaring a different integer is not used.
2. **Exact type identity gates acceleration.** A subclass of `s.Int` may
   override `deserialize`, so `isinstance` would be unsound — only the exact
   field classes below are accelerable.
3. **Per class, all or nothing.** A class is accelerated only if *every*
   field is supported, recursively through `T`. A backend is never asked to
   call back into Python for a field it doesn't understand.
4. **A backend can only ever be a no-op.** A missing module, an ABI
   mismatch, a backend that raises — each records a reason and falls back.
   The single exception is `SEARED_ACCEL=require`, which exists so CI can
   assert the backend actually loaded.

## Accelerable field types

| Tier | Kinds | Status |
|------|-------|--------|
| 1 | `Int`, `Float`, `Str`, `Bool`, `T` | supported |
| 2 | `UUID`, `Date`, `DateTime`, `Time`, `TimeDelta`, `Decimal`, `Bytes`, `Enum`, `Path`, `Dict` | supported |
| 3 | `Tuple`, `Union`, `NDArray`, `PandasFrame`, `PolarsFrame` | deferred |

The field *flags* — `many`, `keyed`, `required`, `default`,
`default_factory`, `data_key`, `dump=False` — are all carried in Tier 1.

Tier 2 does not run as fast as Tier 1, and can't: those kinds spend their
time building Python objects (`uuid.UUID`, `datetime.strptime`, `Decimal`),
which no compiled core removes. Their value is that acceleration is
per-class all-or-nothing — a single `Bytes` field used to disqualify a whole
class, Tier 1 fields included.

Tier 3 is deferred on shape, not effort. `Union` is an UNWRAP field: it
consumes several keys from its *parent's* map and merges its output back at
the parent's level, which a single-pass interpreter isn't built for. `Tuple`
adds per-slot sub-fields. The frame fields cross an optional-import boundary
for workloads dominated by the frame conversion either way.

A class is also declined when it defines its own `__init__` or a
`__post_init__`: a compiled core constructs through `__new__` plus
attribute assignment, which would skip both.

## Introspection

```python
>>> Telemetry.__seared_accel__
AccelInfo(accelerated=True, backend='rusted', reason=None)

>>> HasTuple.__seared_accel__
AccelInfo(accelerated=False, backend=None,
          reason='HasTuple.pair: Tuple is not an accelerated field type')

>>> s.accel_status()
{'mode': 'auto', 'spec_abi': 1, 'available': True, 'backend': 'rusted',
 'backend_version': '0.2.0', 'supports_seared': '>=0.2.8,<0.4', 'reason': None}
```

`__seared_accel__` sits alongside `__seared_fields__` on every decorated
class and always names *why* a class wasn't accelerated. `accel_status()`
is the other half — whether a backend loaded at all.

Both are declared on `Seared` itself, so reading them type-checks; an
undecorated subclass inherits honest defaults (`()` and
`AccelInfo(accelerated=False, reason='class is not decorated with @seared')`)
rather than raising `AttributeError`.

## Control

| Control | Effect |
|---------|--------|
| `@s.seared(accel=False)` | Per-class opt-out. |
| `SEARED_ACCEL=auto` | Default — accelerate where possible. |
| `SEARED_ACCEL=off` | Never accelerate; the backend isn't even imported. |
| `SEARED_ACCEL=require` | Raise if no backend loads. For CI. |
| `SEARED_ACCEL_BACKEND=<module>` | Import that module instead of `rusted`. |

`require` asserts the *backend* loaded, not that every class was
accelerated — a class declining on its own merits is normal in every mode.

## The backend protocol

A backend module exposes:

```python
SPEC_ABI: int                                  # must equal seared's
compile_spec(spec) -> tuple[load, dump] | None # None declines this class
```

with `load(data, format)` and `dump(obj, format)` matching the decorator's
own closures. `SUPPORTS_SEARED` and `__version__` are optional and purely
diagnostic — `SPEC_ABI` is the whole compatibility gate, because seared is
zero-dependency and has no PEP 440 specifier parser to hand.

`tests/refcore.py` is a complete pure-Python implementation of this
protocol. It's the differential-test oracle: seared's entire suite runs
against it with

```sh
SEARED_ACCEL=require SEARED_ACCEL_BACKEND=refcore uv run pytest
```

and must produce identical values *and* identical error messages.
