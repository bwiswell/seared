# `formats/yaml_.py` — YAML codec

Both directions via `PyYAML`, lives behind `seared[yaml]`. Lazy import
— `seared` itself stays YAML-free unless you call `to_yaml` /
`from_yaml`.

## API

```python
Cls.to_yaml(obj) -> str
Cls.from_yaml(source) -> Cls
```

`to_yaml` uses `yaml.safe_dump(..., sort_keys=False)` — preserves
field order from the seared declaration. `from_yaml` uses
`yaml.safe_load` (no arbitrary-tag deserialisation).

`from_yaml` accepts a path-like or a string of YAML content (see
[`_common.md`](_common.md)). Top-level value must be a YAML mapping.

## Missing-extra behaviour

Both methods raise a clear `ImportError` at call time when PyYAML
isn't installed:

```
ImportError: to_yaml/from_yaml requires PyYAML — install via
`pip install seared[yaml]` (or `uv add 'seared[yaml]'`).
```

## Quick example

```python
import seared as s

@s.seared
class Config(s.Seared):
    name: str    = s.Str(required=True)
    workers: int = s.Int(missing=4)

text = """\
name: api
workers: 8
"""
loaded = Config.from_yaml(text)
loaded.workers == 8       # → True

print(Config.to_yaml(loaded))
# name: api
# workers: 8
```
