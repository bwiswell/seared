# `date.py` — `Date`

```python
when: date = s.Date(required=True)
```

`datetime.date` ↔ ISO-8601 date string (`'YYYY-MM-DD'`).

## Options

| Option | Default | |
|---|---|---|
| `format` | `None` | An `strftime` / `strptime` pattern. `None` writes `isoformat()` and reads `date.fromisoformat`; a pattern such as `'%d/%m/%Y'` is used both ways. |

This is the field's own option, not the `format=` carrier hint `dump` and
`load` take, which a `date` field ignores.

## Coercion

`load` takes a `date` as is, and otherwise only a string: anything else,
or a string that doesn't parse, raises `ValidationError` in both modes. A
strict `dump` refuses a value that isn't a `date`; lax mode writes
`str(value)`.
