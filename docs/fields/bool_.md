# `bool.py` — `Bool`

```python
flag: bool = s.Bool(missing=False)
```

Python `bool` ↔ JSON `true` / `false`. Strict on serialize (`validate=True`
raises on non-bool); permissive on deserialize (truthy/falsey values).
