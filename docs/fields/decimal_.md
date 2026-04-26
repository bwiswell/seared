# `decimal_.py` — `Decimal`

```python
amount: Decimal = s.Decimal(required=True)             # string default
units:  Decimal = s.Decimal(required=True, as_number=True)
```

`decimal.Decimal` ↔ string by default (lossless across any precision).

`as_number=True` opts into JSON-native float — lossy beyond IEEE 754
double precision (~15-17 significant digits). Use the default for
financial / scientific data; opt into number-style only when downstream
JSON consumers specifically need numeric types.

## Why string by default

JSON numbers go through `float`, which loses precision past ~17 digits.
A `Decimal('1.23456789012345678901234567890')` round-trips losslessly
as `'1.23456789012345678901234567890'` (string) but as
`1.2345678901234568` if forced through `float`. String-default is the
safe choice; opt out when you've thought about it.

The module file is named `decimal_.py` (trailing underscore) to avoid
shadowing the stdlib `decimal` module; the field is exported as
`s.Decimal`.
