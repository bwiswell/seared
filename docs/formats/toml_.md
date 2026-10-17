# `formats/toml_.py` — TOML codec

Read uses stdlib `tomllib` (Python ≥ 3.11) — no extra needed. Write
requires `tomli-w`, which lives behind `seared[toml]`. The split mirrors
the upstream Python ecosystem's split: read is universal, write is
optional.

## API

```python
Cls.to_toml(obj) -> str          # requires seared[toml]
Cls.from_toml(source, unknown=None) -> Cls     # stdlib only
```

`from_toml` accepts a path-like or a string of TOML content (see
[`_common.md`](_common.md)). Top-level value must be a TOML table.

## No null

TOML has no null. `to_toml` leaves out every `None`-valued key, at any
depth, so a nullable field's `None` (or a `Dict` value's) is written as an
absent key, and that's how `from_toml` reads it back: a nullable field with
a default comes back as the default. A `None` *element* of an array has no
such reading, and `tomli-w` refuses it.

## Missing-extra behaviour

`to_toml` raises a clear `ImportError` at call time when `tomli-w`
isn't installed:

```
ImportError: to_toml requires tomli-w — install via
`pip install seared[toml]` (or `uv add 'seared[toml]'`).
Reading TOML works without the extra (uses stdlib tomllib).
```

`from_toml` works without the extra.

## Quick example

```python
import seared as s

@s.seared
class Settings(s.Seared):
    name: str = s.Str(required=True)
    port: int = s.Int(required=True)

# Read works without seared[toml]:
loaded = Settings.from_toml('name = "service"\nport = 8080\n')

# Write requires the extra:
text = Settings.to_toml(loaded)     # → 'name = "service"\nport = 8080\n'
```
