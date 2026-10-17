# `seared.py` — public re-export module

`seared/seared.py` is the entry point that re-exports the `Seared`
base class and the `@seared` decorator from the private `_core/`
subpackage:

```python
from ._core.base import Seared
from ._core.decorator import seared
```

The package init (`seared/__init__.py`) pulls these together with the
rest of the user-facing API. `import seared as s` gives:

| Group | Names |
|---|---|
| The model | `Seared`, `seared`, `FieldSpec` |
| Fields | `Field`, `Bool`, `Bytes`, `Date`, `DateTime`, `Decimal`, `Dict`, `Enum`, `Float`, `Int`, `Path`, `Str`, `T`, `Time`, `TimeDelta`, `Tuple`, `Union`, `UUID`, and the optional `NDArray`, `PandasFrame`, `PolarsFrame` (each needs its extra only when used) |
| Errors | `SearedError`, `ValidationError` |
| The accelerator | `AccelInfo`, `accel_status` (see [`_core/accel.md`](_core/accel.md)) |
| Schema docs | `document`, `introspect` (see [`doc/index.md`](doc/index.md)) |
| Version | `__version__` |

```python
import seared as s

@s.seared
class Telemetry(s.Seared):
    id: int  = s.Int(required=True)
    x: float = s.Float(required=True)
```

## See also

- [`_core/base.md`](_core/base.md) — `Seared` base class contract.
- [`_core/decorator.md`](_core/decorator.md) — `@seared` decorator
  internals.
- [`_core/errors.md`](_core/errors.md) — exception hierarchy.
- [`fields/`](fields/) — every Field subclass (one doc per file).
- [`formats/index.md`](formats/index.md) — file-format codecs.
- [`overview/architecture.md`](overview/architecture.md) —
  cross-cutting design notes.
