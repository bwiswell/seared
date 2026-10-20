# `json_schema.py` — JSON Schema from a class

```python
from seared.doc import json_schema, field_schema

json_schema(Reading)                       # what load takes, as JSON Schema 2020-12
json_schema(Reading, mode='dump')          # what dump writes
json_schema(Reading, unknown='raise')      # refusing keys the classes don't declare
```

`json_schema` describes a `@seared` class's JSON wire form as a JSON Schema
2020-12 document: for a tool's input and output schemas, an API document, or
a check in another language. `field_schema` is the unit it's built from, for
a caller composing an object of its own. New in 0.4.2. Pure standard
library.

It only describes. seared validates by loading, and stays zero-dependency,
so nothing here validates against a schema; use a JSON Schema library for
that.

## An example

```python
@s.seared
class Point(s.Seared):
    """A point on the floor."""
    x: float = s.Float(required=True, doc='metres east')
    y: float = s.Float(required=True, doc='metres north')

@s.seared(unknown='raise')
class Reading(s.Seared):
    """One reading."""
    id: int = s.Int(required=True)
    at: Point = s.T(Point, required=True)
    seen: dt.datetime | None = s.DateTime(default=None)
    note: str | None = s.Str(default=None, nullable=True)
```

`json_schema(Reading)` gives:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Reading",
  "description": "One reading.",
  "type": "object",
  "properties": {
    "id": {"type": "integer"},
    "at": {"$ref": "#/$defs/Point", "unevaluatedProperties": false},
    "seen": {"type": "string", "format": "date-time"},
    "note": {"type": ["string", "null"]}
  },
  "required": ["id", "at"],
  "unevaluatedProperties": false,
  "$defs": {
    "Point": {
      "title": "Point",
      "description": "A point on the floor.",
      "type": "object",
      "properties": {
        "x": {"type": "number", "description": "metres east"},
        "y": {"type": "number", "description": "metres north"}
      },
      "required": ["x", "y"]
    }
  }
}
```

## Two modes, two promises

A class's input and its output differ, so there are two schemas:

- **`mode='load'`** (the default) is the canonical input: the form a
  producer should send. **An instance valid against it, honouring its
  `format` and `contentEncoding` annotations, loads.** `load` accepts more
  than this: a numeric string for an `Int`, `'yes'` for a `Bool`, a `null`
  on an optional field. The schema leaves that out, so what it describes
  is always safe to send.
- **`mode='dump'`** is what `dump` writes for a valid instance: one `load`
  built, or one constructed with valid values. **`dump`'s output validates
  against it.**

Where they differ:

| | `load` | `dump` |
|---|---|---|
| A `dump=False` field | present | absent |
| `required` | `required=True` fields, and each `Union`'s tag | every key a valid instance always writes: required fields, nullable ones (their `None` is written `null`), and fields with a default other than `None` |
| `default` | the field's static default, in its wire form | none |
| `DateTime`, `Time` | `format: date-time` / `time` | no `format`: a naive value's `isoformat()` has no offset, so it isn't RFC 3339 |
| A nested `Union` payload | required when its variant has a required field (an absent payload loads as `{}`) | always present |
| A `Union`'s `fallback=` | any other tag is accepted | dropped: `dump` writes only the declared tags |

In the example, `json_schema(Reading, mode='dump')` requires `id`, `at`
and `note`, and its `seen` is a plain `{"type": "string"}`.

## Closed or open

A schema is closed, refusing keys its classes don't declare, exactly where
`load` would refuse them ([`../_core/unknown.md`](../_core/unknown.md)):

- `unknown=None` (the default) follows the class's own `unknown=`, as
  `load` does: `Reading` is declared `unknown='raise'`, so its schema is
  closed.
- `'raise'` or `'ignore'` decides for one call.
- A refusing load checks the whole input, nested classes included, so a
  closed schema closes every object in it.
- What `load` never checks stays open: a payload routed to a `Union`'s
  `fallback=`, and a `Dict`'s keys.

Closing uses `unevaluatedProperties: false`, on the root and beside each
`$ref`, never inside a definition. A flat `Union` variant's keys share its
parent's object, so a variant can't be closed alone. Closing where an
object is used lets one definition serve a flat variant, a nested target,
an open schema and a closed one.

## The kinds

The schema describes the JSON carrier. Under msgpack a `Bytes` field
travels as raw bytes, which no schema here describes.

| Field | Schema |
|---|---|
| `Bool` | `{"type": "boolean"}` |
| `Int` | `{"type": "integer"}`, with a keyword for each bound (below) |
| `Float` | `{"type": "number"}`, with a keyword for each bound. A `NaN` or infinity isn't JSON, and no schema has a word for one |
| `Str`, `Path` | `{"type": "string"}`; a `Str`'s lengths and pattern add keywords (below) |
| `UUID` | `{"type": "string", "format": "uuid"}` |
| `Date` | `{"type": "string", "format": "date"}`; with `format=` set, a plain string |
| `DateTime`, `Time` | a string, with `format: date-time` / `time` on input only (above); with `format=` set, a plain string |
| `TimeDelta` | `{"type": "number"}`, in seconds |
| `Decimal` | `{"type": "string"}`, or `{"type": "number"}` with `as_number=True` |
| `Bytes` | `{"type": "string", "contentEncoding": "base64"}`, or `"base16"` with `encoding='hex'` |
| `Enum` | `{"type": …, "enum": [the members' values]}`; values of different types have no one `type` |
| `Dict` | `{"type": "object"}`, its values typed from a `dict[str, X]` annotation when `X` is `str`, `int`, `float` or `bool` |
| `T` | `{"$ref": "#/$defs/Name"}`, with the class under `$defs` |
| `Tuple` | `{"type": "array", "prefixItems": [one per slot], "items": false, "minItems": n, "maxItems": n}` |
| `Union` | an envelope on the parent's object (below) |
| `NDArray` | `{}`: any shape, and a 0-d array dumps as a scalar |
| `PandasFrame`, `PolarsFrame` | `{"type": "array", "items": {"type": "object"}}`, the records both write |

Around each kind:

- **`many`** makes an array of the element (`items`), and **`keyed`** an
  object of it (`additionalProperties`). Elements are never `null`.
- **`nullable`** adds `null` to the whole value: `["integer", "null"]`, or
  an `anyOf` where there's no single `type`.
- **Constraints** (0.4.4) become keywords on the element, in both modes,
  since `load` and a strict `dump` both check them. An `Int`'s or a
  `Float`'s `ge=` is `minimum`, `gt=` `exclusiveMinimum`, `le=` `maximum`
  and `lt=` `exclusiveMaximum`; a `Str`'s `min_length=` and `max_length=`
  are `minLength` and `maxLength`, and its `pattern=` is `pattern`, as
  declared. A pattern is ECMA-262, as JSON Schema's always is, and seared
  takes only one that Python's `re` reads the same way, so a JavaScript
  validator and `load` agree on it. A `null` still satisfies a nullable
  field's. See [`../fields/constraints.md`](../fields/constraints.md).
- **`doc=`** becomes `description`. A class's docstring becomes its
  `description` and its name its `title`, at the root and under `$defs`.
- **A `Tuple` slot** is its field's kind and constraints alone. `Tuple` hands
  each value to its slot field directly, so a slot's `many` and `nullable`
  never apply.

The kind comes from [`s.field_kind`](../fields/kind.md), so a subclass of
`Str` is described as a string. A subclass that narrows its values in an
override is described by its base, so its load schema is wider than its
`load`; one that narrows with the options (a bound, a length, a pattern) is
described by them. A field with no kind can't be described, and
`json_schema` raises `TypeError` naming it (`Reading.raw: Raw has no field
kind, …`), as it does for an enum value JSON can't hold.

## `Union` envelopes

A `Union`'s keys sit on its parent's object, so its schema is an entry in the
parent's `allOf`: the tag as a property, then an `if`/`then` branch per
variant:

```json
{
  "type": "object",
  "properties": {"type": {"type": "string", "enum": ["start", "stop"]}},
  "required": ["type"],
  "allOf": [
    {"if": {"properties": {"type": {"const": "start"}}, "required": ["type"]},
     "then": {"$ref": "#/$defs/Start"}},
    {"if": {"properties": {"type": {"const": "stop"}}, "required": ["type"]},
     "then": {"$ref": "#/$defs/Stop"}}
  ]
}
```

- **Flat** (`payload_key=None`): the branch is the variant, whose keys sit
  beside its parent's.
- **Nested:** the branch is `{"properties": {"<payload_key>": {"$ref": …}}}`.
- **`fallback=`:** on input, the tag is any string, and a final branch
  sends a tag the union doesn't declare to the fallback variant. Its payload
  stays open, as `load` never checks it.

## Nested classes and `$defs`

Each class a field refers to (a `T` target, a `Union` variant or fallback,
a `T` in a `Tuple` slot) is defined once under `$defs` and reached by
`$ref`. A definition is named after its class. When two different classes
share a name, the second takes its module-qualified name
(`mypkg.other.Point`), and is numbered after that if it has to be. Output is
deterministic: the same classes give the same document.

## `field_schema(field, *, mode='load', defs, annotation=None, unknown='ignore')`

One field's schema, for a caller building an object of its own: say, the
schema of a topic's slots alone, each of them optional.

```python
defs = {}
properties = {
    wire: field_schema(f, defs=defs)
    for attr, wire, f in Order.__seared_fields__
    if attr in slots
}
schema = {'type': 'object', 'properties': properties, '$defs': defs}
```

- **`defs`** collects the definitions the field refers to, and its `$ref`s
  point at `#/$defs/…`, so place it under `$defs` in the document. Share
  one dict across a document's fields, emitted with the same `mode` and
  `unknown`.
- **`annotation`** is the field's annotation, which refines a `Dict`'s
  values. `json_schema` reads a class's annotations itself.
- **`unknown='raise'`** closes the objects the field holds.
- **A `Union`'s schema** is its envelope, for the parent's `allOf`.

`DIALECT`, the 2020-12 metaschema's URI, is in `seared.doc.json_schema`
for a document built this way.

## Errors

- **`TypeError`:** `cls` isn't a `@seared` class; a field has no kind; an
  enum value has no JSON form. A field's error names it as `Class.attr`.
- **`ValueError`:** `mode` isn't `'load'` or `'dump'`, or `unknown` isn't
  `'ignore'`, `'raise'` or (for `json_schema`) `None`.
