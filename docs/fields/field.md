# `field.py` — base `Field`

The base class every field type extends. Frozen `@dataclass` with the
common per-field knobs. Subclasses override `serialize` / `deserialize`.

## Common kwargs

| Kwarg | Default | Purpose |
|-------|---------|---------|
| `data_key` | `None` | Wire-key override (defaults to attr name) |
| `keyed` | `False` | Wrap as `dict[str, V]` (per-key apply) |
| `many` | `False` | Wrap as `list[V]` (per-item apply) |
| `required` | `False` | `load` raises when the wire key is absent (or `null`, unless nullable) |
| `nullable` | `False` | `None` is a value: a wire `null` loads as `None`, and `dump` writes `None` as `null` |
| `dump` | `True` | Set `False` to suppress on `dump` |
| `default` | `None` | Static value used when the wire key is absent |
| `default_factory` | `None` | Zero-arg callable invoked per instance instead; the home for mutable defaults |
| `doc` | `None` | Human-facing description; never serialized, surfaced by `seared.doc` |

`required` is checked before any default, so a required field's default
never applies: give a field one or the other.

`default` is held as given, and read directly by construction, `load` and
the accelerator spec; `default_factory` stays deferred and is called once
per instance, winning if both are set. A mutable static default (`list`,
`dict`, `set`, `frozenset`) is deep-copied per instance as a fallback, but
`default_factory` is the better spelling.

`missing=`, the old alias for `default=`, was removed in 0.4.0. Passing it
now raises `TypeError` (an unexpected keyword argument).

## Null on the wire

A wire `null` is a value only on a `nullable=True` field. Anywhere else it
reads as an absent key, so it can't satisfy `required` and doesn't displace
a default. What `load` gives for each case:

| Wire | `required=True` | `default=5` | No default | `nullable=True, default=5` | `nullable=True, required=True` |
|---|---|---|---|---|---|
| Key absent | error | `5` | `None` | `5` | error |
| `null` | error | `5` | `None` | `None` | `None` |
| A value | the value | the value | the value | the value | the value |

`dump` is the mirror: it writes `None` as `null` on a nullable field and
leaves it out everywhere else, where a `null` would read back the same. So a
`None` on a defaulted field comes back as the default; make the field
nullable to keep it.

- **`nullable` and `required` are independent**, as in JSON Schema
  (`required` plus `type: [X, "null"]`). A nullable required field must be
  present, but may be `null`. Annotate a nullable field `X | None`.
- **The same in lax mode.** `validate=False` relaxes coercion, not this.
- **`null` elements** inside a `many` or `keyed` collection are still an
  error. `nullable` is about the field's own value: a nullable list can be
  `null`, but can't hold one.
- **`Union` refuses `nullable=`**: its envelope spans the parent's keys,
  so there is no one key to carry a `null`.
- **Codecs:** YAML's `~` and msgpack's `nil` read as JSON's `null` does.
  TOML has no null, so `to_toml` leaves a nullable `None` out, and it reads
  back as absent; that's the one round trip TOML can't make. CSV has no
  null either: `to_csv` writes `None` as an empty cell, and `from_csv` reads
  an empty or missing cell as null (see
  [`../formats/csv_.md`](../formats/csv_.md#null-the-empty-cell)).

## `serialize(value, validate=True, **kwargs)`

Python value → wire-safe value. `validate=True` raises
`ValidationError` on type / shape mismatch; `validate=False` does
best-effort coercion.

`**kwargs` carries optional codec hints — most notably `format='json' |
'msgpack'`. Fields with native binary representations (`Bytes`,
`NDArray`) act on it; other fields ignore.

## `deserialize(value, validate=True, **kwargs)`

Wire value → Python value. Symmetric with `serialize`.
