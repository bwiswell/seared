# `str.py` — `Str`

```python
name: str = s.Str(required=True)
tags: list = s.Str(many=True, missing=[])
labels: dict = s.Str(keyed=True, missing={})
```

Python `str` ↔ JSON string. `many=True` for lists of strings; `keyed=True`
for `dict[str, str]`. Validation rejects non-string values on serialize.
