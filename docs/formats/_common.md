# `formats/_common.py` — shared codec helpers

Internal module backing every codec's path-vs-content detection.

## `read_source(source) -> str`

Every `from_*` method (JSON, TOML, YAML, CSV) accepts:

- a path-like (`str` or `os.PathLike`) that points at an existing file
  → reads as UTF-8 text
- a string of content → returns it unchanged

The detection rule lives once in `read_source` so callers don't have
to remember per-format quirks. Mirrors the precedent set by
`zeared.SessionConfig.from_yaml`.

```python
from seared.formats._common import read_source

read_source('/path/to/file.json')   # reads the file
read_source('{"x": 1}')             # passes the string through
read_source(42)                     # raises TypeError
```

Non-string non-pathlike inputs (including `bytes`) raise `TypeError`
with the message `expected str path or content`.
