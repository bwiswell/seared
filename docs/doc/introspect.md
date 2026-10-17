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

True for a decorated `@seared` class: a subclass of `Seared`, not `Seared`
itself, with at least one declared field.

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
| `enum` | an `EnumDoc`, for an `Enum` field |
| `nested` | the target class, for a `T` field |
| `variants`, `envelope`, `fallback` | for a `Union`: its `VariantDoc`s, `'flat'` or `` 'nested under `args`' ``, and its fallback class |

`nullable` comes last, with a default, so positional construction from
before it was added still works.

### `EnumDoc` and `VariantDoc`

- `EnumDoc(name, members)`: the enum's name, and `(member name, wire value)`
  pairs.
- `VariantDoc(tag, cls)`: one `Union` tag and its class.
