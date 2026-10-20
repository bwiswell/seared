# `doc/introspect.py` — the intermediate model

`introspect(cls)` reads a `@seared` class into a `SchemaDoc`: a frozen,
render-agnostic description that every renderer consumes, seared's
Markdown one and zeared's wire-aware one alike. Pure standard library.

## `introspect(cls) -> SchemaDoc`

Walks `cls.__seared_fields__` in declaration order, with the class's
resolved annotations for the type strings.

- **Type strings** come from `get_type_hints`, formatted for reading:
  `list[int]`, `float | None` (`None` last). When a forward reference
  won't resolve, the raw annotation strings are used instead, walking the
  MRO; introspection degrades rather than fails.
- **The docstring** is cleaned (`inspect.cleandoc`), and Sphinx roles are
  stripped so it reads as Markdown: ``:class:`Reading` `` becomes
  `` `Reading` ``. Its first line is the `summary` the index uses.
- **References** are the classes the schema points at: `T` targets, `Union`
  variants and a `Union`'s `fallback`, deduplicated in first-seen order.
  The generator documents and links them too.

## `is_seared_class(obj)`

True for a class the `@seared` decorator built, which it marks by setting
`__seared_fields__` on the class it returns. So a decorated class counts
whether or not it subclasses `Seared` (`@zeared` is the same decorator), and
whether or not it has fields, as a `Union` variant may not. The bare `Seared`
base doesn't count, and nor does a subclass of a decorated class that isn't
decorated itself.

Before 0.4.1 it asked for the `Seared` base and at least one field, so a
page could link to a decorated class that the generator never documented.

## The model

All four are frozen, slotted dataclasses.

### `SchemaDoc`

| Field | |
|---|---|
| `cls` | the class |
| `name`, `module` | its `__name__` and `__module__` |
| `doc`, `summary` | the cleaned docstring and its first line, or `None` |
| `fields` | one `FieldDoc` per declared field, in order |
| `is_message` | always `False`: seared never sets it, and zeared documents a `Message` with its own `MessageDoc` |
| `references` | the classes it refers to (see above) |

### `FieldDoc`

| Field | |
|---|---|
| `attr` | the attribute name |
| `wire_key` | the `data_key`, or `None` when it equals `attr` |
| `type_str` | the annotation, formatted |
| `required` | `required=True`, or always for a `Union`, whose tag must be on the wire |
| `default_repr` | what an omitted field holds: `` `5` ``, `` `None` `` (never `null`), `` `Color.RED` ``, `` `<factory: list>` ``, or `—` for a required field |
| `many`, `keyed`, `dump` | the field's options |
| `doc` | the field's `doc=` |
| `nullable` | whether a wire `null` is a value (`nullable=True`), which the annotation can't show |
| `dtype` | an `NDArray`'s declared element type as numpy names it (`'float32'`), or `None` (0.4.1) |
| `kind` | the field's [`FieldKind`](../fields/kind.md), a subclass's being its base's, or `None` (0.4.2) |
| `constraints` | the field's [bounds](../fields/constraints.md) as `(option, value)` pairs in a fixed order, `(('ge', 0), ('lt', 10))`, or `()` (0.4.4) |
| `enum` | an `EnumDoc`, for an `Enum` field |
| `nested` | the target class, for a `T` field |
| `variants`, `envelope`, `fallback` | for a `Union`: its `VariantDoc`s, `'flat'` or `` 'nested under `args`' ``, and its fallback class |

`nullable`, `dtype`, `kind` and `constraints` come last, with defaults, so
positional construction from before they were added still works.

### `EnumDoc` and `VariantDoc`

- `EnumDoc(name, members)`: the enum's name, and `(member name, wire value)`
  pairs.
- `VariantDoc(tag, cls)`: one `Union` tag and its class.
