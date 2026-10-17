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
