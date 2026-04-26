# Architecture

`seared` is a hand-rolled `__slots__` dataclass library — declarative
schemas with validate/coerce semantics on top of `dataclasses.dataclass`.
Replaced marshmallow as the core in 0.1.x; zero runtime dependencies
(`numpy` optional for `NDArray`).

## Decorator pipeline

```python
@s.seared
class Telemetry(s.Seared):
    id: int   = s.Int(required=True)
    x: float  = s.Float(required=True)
    y: float  = s.Float(required=True)
```

When `@s.seared` runs:

1. **Wrap `dataclasses.dataclass`** — the underlying machinery for
   `__slots__`, `__init__`, `__eq__`, `__repr__`. `slots=True` is the default.
2. **Walk fields** — pull every `dataclasses.Field` whose `.default` is
   a `seared.Field` instance. Build a tuple of
   `(attr_name, wire_key, field_instance)` entries; expose as
   `cls.__seared_fields__` for introspection.
3. **Validate UNWRAP constraints** — at most one `UNWRAP` field per
   class historically; relaxed in 0.1.9 to "multiple `UNWRAP` fields
   allowed when their `tag_key` / `payload_key` wire keys are
   disjoint."
4. **Wrap `__init__`** — natural construction (`Telemetry()`) leaves
   `Field` metadata sitting on the instance attributes; the wrapper
   replaces each `Field` with its `missing` value. Mutable `missing`
   values (`list` / `dict` / `set` / `frozenset`) are deep-copied per
   instance to avoid the classic Python shared-default footgun.
5. **Generate `dump` / `load`** — bound classmethods that walk the
   spec list, calling each field's `serialize` / `deserialize`. Both
   accept an optional `format='json'` kwarg (default JSON-safe wire
   shape; `'msgpack'` opts into native binary for `Bytes` and
   `NDArray`).

## Field interface

Every field subclass implements:

```python
class MyField(s.Field):
    def serialize(self, value, validate=True, **kwargs): ...
    def deserialize(self, value, validate=True, **kwargs): ...
```

`**kwargs` carries optional codec hints (`format='msgpack'`) for fields
that have a native-binary representation. Most fields ignore the kwarg.

The base `Field` dataclass holds:
- `data_key: Optional[str]` — wire key override (defaults to attr name).
- `keyed: bool` — wraps as `dict[str, V]`.
- `many: bool` — wraps as `list[V]`.
- `required: bool` — `load` raises if absent.
- `dump: bool` — set `False` to suppress on `dump` (e.g. computed fields).
- `missing: Any` — value when the wire form omits the key.

The decorator's `_apply` helper handles `keyed` / `many` orchestration
once for every field, so subclasses only implement scalar
`serialize(value)` / `deserialize(value)`.

## `UNWRAP` (Union)

A field with `UNWRAP = True` (only `Union` today) bypasses the normal
"one field, one wire key" mapping. Instead, the decorator merges the
field's serialised dict at the parent's top level:

```python
{"action": "start", "speed": 10}    # tag + payload merged flat
```

versus the nested form when `payload_key=` is set:

```python
{"action": "start", "args": {"speed": 10}}
```

Multiple `UNWRAP` fields on the same class are allowed when their
`tag_key` / `payload_key` strings don't collide. Disjointness is
checked at class-definition time.

## Wire-format hint

`dump(obj, format='msgpack')` and `load(data, format='msgpack')` thread
the carrier hint through `_apply` and into each field's `serialize` /
`deserialize` via `**kwargs['format']`. `Bytes` and `NDArray` use it to
emit native bytes (no base64 overhead) when the carrier supports them.
JSON callers pass `format='json'` (default) or omit the kwarg.

## Errors

- `SearedError` — base.
- `ValidationError` — type / shape mismatch on serialize or deserialize.

See [`../_core/errors.md`](../_core/errors.md) for the full hierarchy.

## Per-module docs

- [`../_core/base.md`](../_core/base.md) — `Seared` base class.
- [`../_core/decorator.md`](../_core/decorator.md) — `@seared` decorator
  internals.
- [`../_core/errors.md`](../_core/errors.md) — exception hierarchy.
- [`../fields/`](../fields/) — every Field subclass (one doc per file).
- [`../formats/index.md`](../formats/index.md) — codec orchestrator +
  per-format pages.

That's the entire surface. Everything else is field types.
