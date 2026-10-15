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
| `dump(obj)` | Raises `NotImplementedError` until decorated. |
| `load(data)` | Raises `NotImplementedError` until decorated. |
| `dumps(obj)` | JSON convenience wrapper around `dump`. |
| `loads(data)` | JSON convenience wrapper around `load`. |

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
