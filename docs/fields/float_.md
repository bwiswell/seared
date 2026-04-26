# `float.py` — `Float`

```python
ratio: float = s.Float(required=True)
```

Python `float` ↔ JSON number. `int` values accepted on deserialize and
coerced to `float`. `Decimal` is a separate field (`s.Decimal`).
