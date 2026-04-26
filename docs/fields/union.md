# `_union.py` — `Union` (tagged-payload UNWRAP field)

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

## Two envelope shapes

| Form | `payload_key` | Wire example |
|------|---------------|--------------|
| **Flat** (default) | `None` | `{"type": "start", "speed": 10}` |
| **Nested** | `'args'` | `{"type": "start", "args": {"speed": 10}}` |

Flat is more compact; nested keeps the variant payload self-contained
when `tag_key` collides with a variant field name.

## Unknown tags

Default behaviour: `load` raises `ValidationError` on a tag not in
`variants`.

`Union(variants={...}, default=Unknown)` opts into graceful fallback
— unknown tags coerce to the supplied default class. Useful for
schema evolution: old consumers receive new variants as a generic
fallback variant rather than crashing.

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
