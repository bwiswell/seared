# `union.py` — `Union` (tagged-payload UNWRAP field)

```python
@s.seared
class Cmd(s.Seared):
    action: object = s.Union(
        variants={'start': Start, 'stop': Stop},
    )
```

Tagged-union field implementing the `{tag, payload}` envelope pattern.
Marked `UNWRAP = True`, so the seared decorator merges its serialised
form at the parent's top-level wire dict rather than nesting under one
key.

## Options

| Option | Default | |
|---|---|---|
| `variants` | required | `{tag: VariantCls}`: the tags this union knows, each with its `@seared` class. Must be non-empty. |
| `tag_key` | `'type'` | The wire key that holds the tag. |
| `payload_key` | `None` | `None` merges the variant's fields beside the tag (flat); a string nests them under that key. |
| `fallback` | `None` | The class an unknown tag loads as (see [Unknown tags](#unknown-tags)). |
| `dump` | `True` | `False` leaves the whole envelope out of `dump`. |
| `doc` | `None` | Text for generated schema pages. |

`many`, `keyed`, `required` and `data_key` are accepted and ignored: the
envelope is always one value spread over the parent's keys, and always
required, since a missing tag raises. `default=` (other than `None`),
`default_factory=` and `nullable=True` raise `TypeError`, for the reasons
below.

## Two envelope shapes

| Form | `payload_key` | Wire example |
|------|---------------|--------------|
| **Flat** (default) | `None` | `{"type": "start", "speed": 10}` |
| **Nested** | `'args'` | `{"type": "start", "args": {"speed": 10}}` |

Flat is more compact; nested keeps the variant payload self-contained
when `tag_key` collides with a variant field name.

## Unknown tags

Default behaviour: `load` raises `ValidationError` on a tag not in
`variants`. A missing or unknown tag's error points at the tag key
(`Control.action: Union: unknown tag 'halt'; …`). An error inside the
payload sits under `payload_key` for a nested envelope
(`Control.args.speed`), and at the parent's own keys for a flat one
(`Control.speed`), since that's where the payload's fields are.

`Union(variants={...}, fallback=Unknown)` opts into graceful fallback
— unknown tags coerce to the supplied class. Useful for schema
evolution: old consumers receive new variants as a generic fallback
variant rather than crashing.

Before 0.4.0 this option was spelled `default=`. From 0.4.0 `default=`
means what it means on every other field, the value an absent key gets, and
a `Union` has none: its envelope is always populated on load, and an
omitted one in a constructor call is `None`. So `default=`, and
`default_factory=`, raise `TypeError` pointing at `fallback=`, rather
than quietly change meaning. `default=None` is still accepted.

## Unknown keys

A variant loads through its own bare load, `Variant.__seared_load__`, with
no `unknown=` in front of it: a flat envelope hands the variant its
parent's keys too, so a variant that refused unknown keys would refuse its
own envelope. An outer refusing load still checks the envelope: it knows
the `tag_key`, the `payload_key` or the selected variant's keys, and walks
a nested payload. Two cases report nothing, since no declared variant says
which keys are expected: a payload routed to `fallback=`, and a flat
envelope with a missing or unknown tag. See
[`../_core/unknown.md`](../_core/unknown.md).

## Null

A `null` tag is a missing one, and raises. A `null` payload under
`payload_key` is an absent one: the variant loads from its own defaults,
as it would with no payload key at all.

`nullable=True` raises `TypeError`. A `Union`'s envelope spans its
parent's keys (the tag, and the payload key or the variant's own fields),
so there is no one key a `null` could sit on.

## Multiple Unions per class

A class may declare multiple `Union` fields when each Union's wire
keys (`tag_key`, `payload_key`) are disjoint. The decorator validates
disjointness at class-definition time:

```python
@s.seared
class Cmd(s.Seared):
    motion: object = s.Union(variants={'up': Up, 'down': Down}, tag_key='motion_type')
    io:     object = s.Union(variants={'read': Read, 'write': Write}, tag_key='io_type')
```

Sharing a `tag_key` (or `payload_key`) across Unions raises
`TypeError` at class definition.
