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
| `accel` | `True` | `False` keeps the class on the pure-Python path even when an accelerator is installed (see [`accel.md`](accel.md)) |

## What `_build` does

1. **Wrap `dataclasses.dataclass`** — base machinery for `__slots__`,
   `__init__`, `__eq__`, `__repr__`.
2. **Walk fields** — pull every `dataclasses.Field` whose `.default` is
   a `seared.Field` instance. Build a `FieldSpec(attr, wire, field)` per
   declared field (a named tuple; see [`base.md`](base.md)); expose the
   tuple of them as `cls.__seared_fields__`.
3. **Validate UNWRAP disjointness** — multiple `UNWRAP` fields (today
   only `Union`) are allowed when their `tag_key` / `payload_key`
   strings don't collide. Single-UNWRAP-per-class was the pre-0.1.9
   constraint; relaxed to per-key-disjoint.
4. **Wrap `__init__`** — natural construction (`Foo()`) leaves `Field`
   metadata sitting on instance attributes. The wrapper substitutes
   each `Field` instance with its `missing` value. Mutable `missing`
   values (`list`, `dict`, `set`, `frozenset`) are deep-copied
   per-instance to avoid the classic Python shared-default footgun.
   A `__post_init__` is wrapped to substitute *first*: the dataclass
   `__init__` calls the hook before it returns, so without it the hook
   would read an omitted field as its (truthy) `Field` object — where
   `load`, which resolves every omitted field before constructing, hands
   it the real default. An inherited hook is wrapped again by each
   subclass, so it sees the subclass's omitted fields resolved too.
5. **Generate `dump` / `load`** — bound classmethods that walk the
   spec list, calling each field's `serialize` / `deserialize`. Both
   accept an optional `format=` kwarg threaded through to the field
   methods.
6. **Attach format codecs** — calls `_attach_format_methods` (from
   `seared.formats`) to wire `to_json` / `from_json` / `to_csv` /
   etc. onto the class.

## Load semantics

What the generated `load` does with each declared field, in order:

1. **Wire key present** → the value goes through the field (via `_apply`).
   A `null` value short-circuits to `None` before the field ever sees it,
   whatever the field's `required` / default, so a wire `null` *overrides*
   a default rather than counting as absent.
2. **Absent, `required=True`** → `ValidationError('Cls.attr is required')`.
   "Required" means the key is present, not that the value is non-null.
3. **Absent, `default_factory`** → a fresh value from the factory.
4. **Absent, otherwise** → the static default (`None` if none was given).

Then `cls(**kwargs)` builds the instance. Two more rules round it out:

- **Unknown wire keys are ignored**, so an older consumer can read a newer
  producer's payload. The family relies on it to remove fields outright.
- **Construction doesn't check `required`.** `Cls()` runs the dataclass
  `__init__`, which leaves an omitted required field as `None`; the type
  checker flags the call, and only `load` raises.

`dump` is the mirror image: it skips `dump=False` fields and `None` values,
so `None` and "absent" are the same thing on the wire.

0.4.0 changes rules 1 and 2: `null` reads as absent unless a field is
declared nullable, so a required field rejects it.

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
