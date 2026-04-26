# `formats/json_.py` — JSON codec

Stdlib-only. No extras required. Always available.

## API

```python
Cls.to_json(obj, *, indent=None, **kwargs) -> str
Cls.from_json(source) -> Cls
```

`to_json` passes `**kwargs` straight to `json.dumps` — useful for
`sort_keys=True`, `separators=...`, `default=...`, etc. The `indent`
kwarg is split out only because callers reach for it most often.

`from_json` accepts a path-like or a string of JSON content (see
[`_common.md`](_common.md) for the detection rule). The top-level
JSON value must be an object — top-level arrays raise `ValueError`
because seared dataclasses aren't list-typed at the root.

## Quick example

```python
import seared as s

@s.seared
class Telemetry(s.Seared):
    id: int   = s.Int(required=True)
    x: float  = s.Float(required=True)

t = Telemetry(id=1, x=3.14)
print(Telemetry.to_json(t, indent=2))
# {
#   "id": 1,
#   "x": 3.14
# }
loaded = Telemetry.from_json('{"id": 2, "x": 1.5}')
loaded == Telemetry(id=2, x=1.5)            # → True
```
