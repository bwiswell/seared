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
| `unknown` | `'ignore'` | `'raise'` refuses a key the class doesn't declare, wherever it's the class loaded; a call's own `unknown=` overrides it. For configs, never wire messages (see [`unknown.md`](unknown.md)). Anything but the two values is a `ValueError` |

## What `_build` does

1. **Wrap `dataclasses.dataclass`** — base machinery for `__slots__`,
   `__init__`, `__eq__`, `__repr__`. The class keeps its own `__doc__`:
   `dataclass()` writes its generated signature there when the class has no
   docstring, and the decorator puts the `None` back (0.4.1), so schema docs
   and generated types don't read the signature as the class's description.
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
   each `Field` instance with its default (a `default_factory` call, or
   the static `default`). Mutable `default`
   values (`list`, `dict`, `set`, `frozenset`) are deep-copied
   per-instance to avoid the classic Python shared-default footgun.
   A `__post_init__` is wrapped to substitute *first*: the dataclass
   `__init__` calls the hook before it returns, so without it the hook
   would read an omitted field as its (truthy) `Field` object — where
   `load`, which resolves every omitted field before constructing, hands
   it the real default. An inherited hook is wrapped again by each
   subclass, so it sees the subclass's omitted fields resolved too.
5. **Offer the class to the accelerator** — `try_compile` (from
   `_core.accel`) returns a compiled `(load, dump)` pair when a backend
   takes the class, and otherwise records why on `cls.__seared_accel__`.
   See [`accel.md`](accel.md).
6. **Generate `dump` / `load`** — the compiled pair, or else bound
   classmethods that walk the spec list, calling each field's
   `serialize` / `deserialize`. Both accept an optional `format=` kwarg
   threaded through to the field methods. The public `load` takes
   `unknown=` too, in front of the class's own load: one of two shapes,
   picked by the class's default, so an ignoring class pays one `is None`
   test per call. The own load is kept as `__seared_load__`, which nested
   `T` and `Union` fields call (see [`unknown.md`](unknown.md)).
7. **Attach format codecs** — calls `_attach_format_methods` (from
   `seared.formats`) to wire `to_json` / `from_json` / `to_csv` /
   etc. onto the class.

## Load semantics

What the generated `load` does with each declared field, in order:

1. **Wire key present with a value** → the value goes through the field
   (via `_apply`).
2. **Wire key present with `null`, on a `nullable=True` field** → `None`,
   whatever the default. A nullable required field is satisfied by it.
3. **Absent, or `null` on a field that isn't nullable** → the two read the
   same:
   - **`required=True`** → `ValidationError`, reading
     `Cls.wire: required key missing` (the path names the wire key; see
     [`errors.md`](errors.md));
   - **a `default_factory`** → a fresh value from the factory;
   - **otherwise** → the static default (`None` if none was given).

Then `cls(**kwargs)` builds the instance. Three more rules round it out:

- **Unknown wire keys are ignored** by default, so an older consumer can
  read a newer producer's payload. The family relies on it to remove fields
  outright. `unknown='raise'` refuses them instead, checking the whole input
  before this load runs (see [`unknown.md`](unknown.md)).
- **Construction doesn't check `required`.** `Cls()` runs the dataclass
  `__init__`, which leaves an omitted required field as `None`; the type
  checker flags the call, and only `load` raises.
- **The same in lax mode.** `validate=False` relaxes coercion, not these
  rules.

`dump` is the mirror image: it skips `dump=False` fields, and `None`
values except on a nullable field, which it writes as `null`. Leaving a
`None` out loses nothing a `null` would have kept, since `load` reads the
two alike. The full table is in
[`../fields/field.md`](../fields/field.md#null-on-the-wire).

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
`serialize` / `deserialize` via `**kwargs['format']`. `Bytes` uses it to
emit native bytes (no base64 overhead) when the carrier supports them,
and `T` and `Tuple` pass it on to what they hold. JSON callers pass `format='json'` (default) or
omit the kwarg.

## `UNWRAP` field handling

A field whose class has `UNWRAP = True` (only `Union` today) is
serialised inline at the parent's top-level wire dict rather than
nested under a single wire key. See [`../fields/union.md`](../fields/union.md)
for the envelope shapes.

Whether a field is `UNWRAP` is settled once per class, when `dump` and
`load` are generated, and carried in the tuples their loops walk. Asking
per field on every call cost a function call each time.
