# `int_.py` — `Int`

```python
count: int = s.Int(required=True)
```

Python `int` ↔ JSON number. Serialize takes an `int` (and, with
`validate=True`, refuses anything else, `bool` included).

Deserialize takes an `int` as is. Beyond that:

| Input | `validate=True` | `validate=False` |
|-------|-----------------|------------------|
| an integral `float` (`3.0`) | `3` | `3` |
| a fractional `float` (`3.7`) | raises `ValidationError` | truncated: `3` |
| a numeric string (`'42'`, `' 7 '`) | `42` | `42` |
| a `bool` | raises `ValidationError` | `1` / `0` |
| `inf`, `nan`, `'3.0'`, anything else | raises `ValidationError` | raises `ValidationError` |

Strict mode refuses only what it can't take without losing data, so a
fractional float is an error rather than a silent truncation. Numeric
strings stay accepted in both modes: string-only sources, such as Zenoh
topic captures, decode through them.

Before 0.4.0, strict mode truncated `3.7` to `3`, and `inf` raised a bare
`OverflowError` in both modes, which `except s.ValidationError` didn't
catch. An int-valued [`Enum`](enum_.md) follows the same rules.

## Bounds

```python
retries: int = s.Int(ge=0, lt=10, default=3)
```

`ge=`, `gt=`, `le=` and `lt=` bound the value (0.4.4), each an `int`. A
strict `load` checks them after the coercion above, so `'42'` and `42.0`
are checked as `42`, and a strict `dump` checks them too; lax mode skips
them. `json_schema` writes them as `minimum` and the rest. See
[`constraints.md`](constraints.md).
