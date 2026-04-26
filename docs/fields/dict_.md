# `_dict.py` — `Dict`

```python
metadata: dict = s.Dict(missing={})
```

Pass-through `dict` field. No deep-validation — the values can be any
JSON-safe shape. For typed maps use `s.Str(keyed=True)` (or any other
field with `keyed=True`).

Module name leading underscore avoids shadowing stdlib `dict`; field
exported as `s.Dict`.
