# `_core/decorator.py` — `@seared` decorator

Turns a `Seared` subclass into a serialisable dataclass. Wraps
`@dataclass(slots=True)`, generates `dump` / `load` classmethods,
populates `__seared_fields__`, and wires per-format codec methods (see
[`../formats/index.md`](../formats/index.md)).

## Signature

```python
@s.seared                                  # parameter-free
class Foo(s.Seared): ...

@s.seared(slots=True, validate=True)       # explicit kwargs
class Foo(s.Seared): ...
```

| Kwarg | Default | Effect |
|-------|---------|--------|
| `slots` | `True` | Pass-through to `@dataclass(slots=...)` |
| `validate` | `True` | `dump` / `load` raise on type mismatch when `True`; best-effort coerce when `False` |

## What `_build` does

1. **Wrap `dataclasses.dataclass`** — base machinery for `__slots__`,
   `__init__`, `__eq__`, `__repr__`.
2. **Walk fields** — pull every `dataclasses.Field` whose `.default` is
   a `seared.Field` instance. Build a `(attr, wire, Field)` tuple per
   declared field; expose as `cls.__seared_fields__`.
3. **Validate UNWRAP disjointness** — multiple `UNWRAP` fields (today
   only `Union`) are allowed when their `tag_key` / `payload_key`
   strings don't collide. Single-UNWRAP-per-class was the pre-0.1.9
   constraint; relaxed to per-key-disjoint.
4. **Wrap `__init__`** — natural construction (`Foo()`) leaves `Field`
   metadata sitting on instance attributes. The wrapper substitutes
   each `Field` instance with its `missing` value. Mutable `missing`
   values (`list`, `dict`, `set`, `frozenset`) are deep-copied
   per-instance to avoid the classic Python shared-default footgun.
5. **Generate `dump` / `load`** — bound classmethods that walk the
   spec list, calling each field's `serialize` / `deserialize`. Both
   accept an optional `format=` kwarg threaded through to the field
   methods.
6. **Attach format codecs** — calls `_attach_format_methods` (from
   `seared.formats`) to wire `to_json` / `from_json` / `to_csv` /
   etc. onto the class.

## `_apply` orchestration

```python
def _apply(f, v, op, validate, *, format='json'): ...
```

Handles `keyed` / `many` orchestration once for every field — subclasses
only implement scalar `serialize(value)` / `deserialize(value)`.
`keyed=True` maps over a dict; `many=True` maps over a list.

## `format=` carrier hint

`Cls.dump(obj, format='msgpack')` and `Cls.load(data, format='msgpack')`
thread the carrier hint through `_apply` and into each field's
`serialize` / `deserialize` via `**kwargs['format']`. `Bytes` and
`NDArray` use it to emit native bytes (no base64 overhead) when the
carrier supports them. JSON callers pass `format='json'` (default) or
omit the kwarg.

## `UNWRAP` field handling

A field whose class has `UNWRAP = True` (only `Union` today) is
serialised inline at the parent's top-level wire dict rather than
nested under a single wire key. See [`../fields/union.md`](../fields/union.md)
for the envelope shapes.
