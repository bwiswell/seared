# `field.py` — base `Field`

The base class every field type extends. Frozen `@dataclass` with the
common per-field knobs. Subclasses override `serialize` / `deserialize`.

## Common kwargs

| Kwarg | Default | Purpose |
|-------|---------|---------|
| `data_key` | `None` | Wire-key override (defaults to attr name) |
| `keyed` | `False` | Wrap as `dict[str, V]` (per-key apply) |
| `many` | `False` | Wrap as `list[V]` (per-item apply) |
| `required` | `False` | `load` raises if absent and no `missing` |
| `dump` | `True` | Set `False` to suppress on `dump` |
| `missing` | `None` | Value used when wire-key absent |

`required=True` and `missing=...` are mutually meaningful: `required`
is checked before `missing`, so requiring a field with a missing default
is a contradiction (`missing` will never apply).

Mutable `missing` values (`list`, `dict`, `set`, `frozenset`) are
deep-copied per-instance to avoid the shared-default footgun.

## `serialize(value, validate=True, **kwargs)`

Python value → wire-safe value. `validate=True` raises
`ValidationError` on type / shape mismatch; `validate=False` does
best-effort coercion.

`**kwargs` carries optional codec hints — most notably `format='json' |
'msgpack'`. Fields with native binary representations (`Bytes`,
`NDArray`) act on it; other fields ignore.

## `deserialize(value, validate=True, **kwargs)`

Wire value → Python value. Symmetric with `serialize`.
