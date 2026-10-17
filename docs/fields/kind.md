# `kind.py` — `FieldKind` and `field_kind`

```python
import seared as s

s.field_kind(s.Int())             # FieldKind.INT
s.field_kind(Order.__seared_fields__[0].field)
s.field_kind(s.Str)               # a field class answers too: FieldKind.STR
```

A field's kind says which of seared's built-in fields it is. It's for code
that maps fields onto something else: a JSON Schema, a column type, a check
that a value fits in one key segment. New in 0.4.2.

## Why not `type(field).__name__`

A table keyed on the class name misses every subclass. A field that
subclasses `Str` to check its value more strictly still travels as a
string, but `type(field).__name__` says it's something else, so it fell
out of every such table. Each built-in field class names its kind in a
`KIND` class attribute instead, and a subclass inherits it:

```python
class SecretRef(s.Str):
    def deserialize(self, value, validate=True, **kwargs):
        text = super().deserialize(value, validate, **kwargs)
        ...  # refuse a value that isn't a secret's name
        return text

s.field_kind(SecretRef())         # FieldKind.STR
```

## The kinds

| `FieldKind` | Value | Field |
|---|---|---|
| `INT` | `'int'` | `Int` |
| `FLOAT` | `'float'` | `Float` |
| `STR` | `'str'` | `Str` |
| `BOOL` | `'bool'` | `Bool` |
| `NESTED` | `'nested'` | `T` |
| `UUID` | `'uuid'` | `UUID` |
| `DATE` | `'date'` | `Date` |
| `DATETIME` | `'datetime'` | `DateTime` |
| `TIME` | `'time'` | `Time` |
| `TIMEDELTA` | `'timedelta'` | `TimeDelta` |
| `DECIMAL` | `'decimal'` | `Decimal` |
| `BYTES` | `'bytes'` | `Bytes` |
| `ENUM` | `'enum'` | `Enum` |
| `PATH` | `'path'` | `Path` |
| `DICT` | `'dict'` | `Dict` |
| `TUPLE` | `'tuple'` | `Tuple` |
| `UNION` | `'union'` | `Union` |
| `NDARRAY` | `'ndarray'` | `NDArray` |
| `PANDAS` | `'pandas'` | `PandasFrame` |
| `POLARS` | `'polars'` | `PolarsFrame` |

`FieldKind` is a `StrEnum`, so a kind compares equal to its value
(`FieldKind.NESTED == 'nested'`). The values are the accelerator spec's
kind names, so there is one vocabulary for both.

The kind is all `field_kind` reports. What else a field declares (a
`Bytes` field's `encoding`, a `T`'s `schema`, a `Union`'s `variants`) is
on the field itself, as the attributes each field's page documents.

## A subclass that changes the wire form

A subclass that writes something other than its base's wire form names its
own kind, or `None` for no kind:

```python
class Seconds(s.Float):
    KIND = s.FieldKind.TIMEDELTA      # or KIND = 'timedelta'

class Opaque(s.Str):
    KIND = None                       # s.field_kind(Opaque()) is None
```

A class that subclasses `Field` directly has no kind until it names one.
`KIND` is checked where it's declared: a name that isn't a kind raises
`TypeError` when the class is defined. `field_kind` gives `None` for
anything that isn't a field.

## The accelerator

The accelerator reads the same names, but only off the exact built-in
class. A subclass overrides `serialize` or `deserialize`, and the compiled
path would never run the override, so a subclass declines acceleration
whatever its kind (see [`../_core/accel.md`](../_core/accel.md)).
