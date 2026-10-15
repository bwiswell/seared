# `field.py` — base `Field`

The base class every field type extends. Frozen `@dataclass` with the
common per-field knobs. Subclasses override `serialize` / `deserialize`.

## Common kwargs

| Kwarg | Default | Purpose |
|-------|---------|---------|
| `data_key` | `None` | Wire-key override (defaults to attr name) |
| `keyed` | `False` | Wrap as `dict[str, V]` (per-key apply) |
| `many` | `False` | Wrap as `list[V]` (per-item apply) |
| `required` | `False` | `load` raises when the wire key is absent |
| `dump` | `True` | Set `False` to suppress on `dump` |
| `default` | `None` | Static value used when the wire key is absent |
| `default_factory` | `None` | Zero-arg callable invoked per instance instead; the home for mutable defaults |
| `doc` | `None` | Human-facing description; never serialized, surfaced by `seared.doc` |
| `missing` | `None` | **Deprecated** alias for `default`; warns, and is removed in 0.4.0 |

`required` is checked before any default, so a required field's default
never applies: give a field one or the other.

`default=` folds into the `missing` attribute at construction, which is
where the decorator reads the resolved value; `default_factory` stays
deferred and is called once per instance. A mutable static default (`list`,
`dict`, `set`, `frozenset`) is deep-copied per instance as a fallback, but
`default_factory` is the better spelling.

## `serialize(value, validate=True, **kwargs)`

Python value → wire-safe value. `validate=True` raises
`ValidationError` on type / shape mismatch; `validate=False` does
best-effort coercion.

`**kwargs` carries optional codec hints — most notably `format='json' |
'msgpack'`. Fields with native binary representations (`Bytes`,
`NDArray`) act on it; other fields ignore.

## `deserialize(value, validate=True, **kwargs)`

Wire value → Python value. Symmetric with `serialize`.
