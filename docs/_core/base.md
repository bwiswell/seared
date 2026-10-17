# `_core/base.py` — `Seared` base class

The marker base class every seared dataclass subclasses. Bare bones —
the heavy lifting comes from the `@seared` decorator (see
[`decorator.md`](decorator.md)).

```python
import seared as s

@s.seared
class Telemetry(s.Seared):           # subclass of Seared
    id: int  = s.Int(required=True)
    x: float = s.Float(required=True)
```

## Surface

| Attribute / Method | Behaviour |
|--------------------|-----------|
| `__seared_fields__: ClassVar[tuple[FieldSpec, ...]]` | Empty tuple on the bare base; populated by the decorator with one `FieldSpec` per declared field, in order. |
| `__seared_accel__: ClassVar[AccelInfo]` | Whether the compiled accelerator took the class, and the reason if not (see [`accel.md`](accel.md)). On the bare base: not accelerated, "class is not decorated with @seared". |
| `dump(obj, format='json')` | Raises `NotImplementedError` until decorated. `format` is the carrier hint the decorator threads into every field (see [`decorator.md`](decorator.md#format-carrier-hint)). |
| `load(data, format='json')` | Raises `NotImplementedError` until decorated. `format` as for `dump`. |
| `dumps(obj, **kwargs)` | JSON convenience wrapper around `dump`; `**kwargs` pass through to `json.dumps`, as they do for `to_json`. |
| `loads(data)` | JSON convenience wrapper around `load`. |
| `to_json` / `from_json`, `to_toml` / `from_toml`, `to_yaml` / `from_yaml`, `to_csv` / `from_csv` | The per-format codecs. Declared here so calls on a decorated class type-check; the decorator attaches the real ones (see [`../formats/index.md`](../formats/index.md)). |

`dump` and `load` here must stay signature-identical to what the decorator
attaches; `tests/_core/test_base.py` asserts it.

`dumps` writes a `NaN` or infinite float as a bare `NaN` / `Infinity`,
which is Python's `json` default: Python reads it back, but standard JSON
parsers, browsers included, refuse it. Pass `allow_nan=False` for JSON
headed anywhere but Python, and `dumps` raises `ValueError` instead. The
default stays, because msgpack and Python consumers carry these values on
purpose.

The class is intentionally lightweight: it exists so `isinstance(obj,
Seared)` is meaningful, and so type-checkers see a concrete base for
your dataclasses. Real serialisation comes from the decorator.

## Re-export

`Seared` is re-exported at the package root: `s.Seared` and `from
seared import Seared` both resolve to this class.

## `FieldSpec`

```python
class FieldSpec(NamedTuple):
    attr: str     # the Python attribute name
    wire: str     # the wire key: data_key when set, else attr
    field: Field  # the declared field instance
```

A named tuple, so `for attr, wire, field in Cls.__seared_fields__` unpacks it
exactly as it did when the entries were plain triples (before 0.3.3). The
names are for code that reads one entry at a time, and the types let a
checker see that `field` is a `Field`. Re-exported as `s.FieldSpec`.
