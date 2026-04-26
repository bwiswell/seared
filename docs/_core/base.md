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
| `__seared_fields__: ClassVar[tuple]` | Empty tuple on the bare base; populated by the decorator with `(attr, wire_key, Field)` triples. |
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
