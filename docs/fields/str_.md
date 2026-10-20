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

## Lengths and a pattern

```python
handle: str = s.Str(min_length=3, max_length=32, pattern=r'^[a-z0-9_]+$', required=True)
```

`min_length=` and `max_length=` bound the length, in code points, and
`pattern=` is a regex the string must contain a match for (0.4.4). A strict
`load` and a strict `dump` check them, the lengths first; lax mode skips
them. A pattern is JSON Schema's, an ECMA-262 regex, and must stay within
the subset Python reads the same way: `\d` is refused, with `[0-9]` as the
portable spelling. A pattern's message never shows the value.
`json_schema` writes them as `minLength`, `maxLength` and `pattern`. See
[`constraints.md`](constraints.md).
