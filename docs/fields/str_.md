# `str_.py` — `Str`

```python
name: str = s.Str(required=True)
tags: list = s.Str(many=True, default_factory=list)
labels: dict = s.Str(keyed=True, default_factory=dict)
```

Python `str` ↔ JSON string. `many=True` for lists of strings; `keyed=True`
for `dict[str, str]`.

## Coercion

`load` takes a string as is. Anything else is refused in strict mode, and
in lax mode becomes `str(value)`: `5` reads as `'5'` and `True` as
`'True'`. `dump` mirrors it: strict refuses a value that isn't a string,
and lax writes `str(value)`.
