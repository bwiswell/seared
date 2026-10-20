# `float_.py` — `Float`

```python
ratio: float = s.Float(required=True)
```

Python `float` ↔ JSON number. `Decimal` is a separate field (`s.Decimal`).

## Coercion

| On `load` | Strict | Lax |
|---|---|---|
| a float or an int | `float(value)` | `float(value)` |
| a numeric string (`'2.5'`, `'nan'`, `'inf'`) | parsed | parsed |
| any other string | error | error |
| a bool | error | `1.0` / `0.0` |
| anything else | error | error |

A strict `dump` takes a float or an int, never a bool; lax mode writes
`float(value)`.

## Bounds

```python
interval_s: float = s.Float(ge=5, le=3600, default=60.0)
```

`ge=`, `gt=`, `le=` and `lt=` bound the value (0.4.4), each a finite
number. A strict `load` checks them after the coercion above, and a strict
`dump` checks them too; lax mode skips them. A bounded field refuses `nan`,
which an unbounded one still reads, and an infinity fails an upper bound.
`json_schema` writes them as `minimum` and the rest. See
[`constraints.md`](constraints.md).
