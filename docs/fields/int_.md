# `int.py` — `Int`

```python
count: int = s.Int(required=True)
```

Python `int` ↔ JSON number. `validate=True` rejects floats / strings on
serialize; `validate=False` coerces via `int()`.
