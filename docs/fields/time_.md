# `time_.py` — `Time`

```python
clock: time = s.Time(required=True)
```

`datetime.time` ↔ ISO-8601 time string (`'HH:MM:SS[.fff]'`).

## Options

| Option | Default | |
|---|---|---|
| `format` | `None` | An `strftime` / `strptime` pattern. `None` writes `isoformat()` and reads `time.fromisoformat`; a pattern such as `'%H:%M'` is used both ways. |

This is the field's own option, not the `format=` carrier hint `dump` and
`load` take, which a `time` field ignores.

## Coercion

`load` takes a `time` as is, and otherwise only a string: anything else,
or a string that doesn't parse, raises `ValidationError` in both modes. A
strict `dump` refuses a value that isn't a `time`; lax mode writes
`str(value)`.
