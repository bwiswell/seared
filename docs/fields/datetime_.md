# `datetime_.py` — `DateTime`

```python
ts: datetime = s.DateTime(required=True)
```

`datetime.datetime` ↔ ISO-8601 string. Module-name trailing underscore
avoids shadowing the stdlib `datetime` module; exported as
`s.DateTime`.

## Options

| Option | Default | |
|---|---|---|
| `format` | `None` | An `strftime` / `strptime` pattern. `None` writes `isoformat()` and reads `datetime.fromisoformat`; a pattern such as `'%Y-%m-%d %H:%M'` is used both ways. |

This is the field's own option, not the `format=` carrier hint `dump` and
`load` take, which a `datetime` field ignores. A pattern's time zone
handling is its own: `%z` reads and writes an offset, and without it a
naive value stays naive.

## Coercion

`load` takes a `datetime` as is, and otherwise only a string: anything else,
or a string that doesn't parse, raises `ValidationError` in both modes. A
strict `dump` refuses a value that isn't a `datetime`; lax mode writes
`str(value)`.
