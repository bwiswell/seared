# `formats/csv_.py` — CSV codec

Class-method-only, flat-only. A CSV file is a list of records (one row
per dataclass instance), so the API is class-level rather than per-
instance:

```python
rows = Row.from_csv(source)            # → list[Row]
text = Row.to_csv([row1, row2, row3])  # → str
```

Stdlib-only — no extras required.

## What "flat" means

Nested fields raise `TypeError` at call time:

- `T(...)` — nested seared class
- `Union(...)` — tagged union
- `NDArray()` — numpy array
- `Tuple(...)` — declared tuple
- `PandasFrame()` / `PolarsFrame()` — DataFrame

`many=True` / `keyed=True` collections also raise — CSV cells can't
hold structured data, and flatten-and-rehydrate is its own design
problem deferred to a future release.

`Date`, `DateTime`, `Decimal`, `Path`, `UUID`, `TimeDelta` etc.
round-trip via their existing string serialisation in `dump` / `load`
— CSV gets the JSON-safe string form for free.

## Columns

`to_csv` writes one column per field that `dump` writes, headed by its wire
key: a field's `data_key` where it has one, its attribute name otherwise.
That's the name `from_csv` reads the column back by. A `dump=False` field
gets no column, since `dump` never writes it.

## Null: the empty cell

CSV has no null, so the empty cell stands in for one:

- **`to_csv`** writes every `None` as an empty cell: a field `dump` leaves
  out, and a nullable field's `None`.
- **`from_csv`** reads an empty cell as null, and so is a short row's
  missing cell. 0.4.0's null rule then applies (see
  [`../fields/field.md`](../fields/field.md#null-on-the-wire)): the field
  takes its default, a nullable one keeps `None`, and a required one raises
  `required key missing`.

So a `None` round-trips through CSV for every flat field kind. The one
value that can't is the empty string: it shares the empty cell with `None`,
so `''` comes back as the field's default.

Before 0.4.0 the header named attributes, so any `data_key` field made
`to_csv` fail, and an empty cell reached the field as `''`. A `Str` loaded
it as `''`, and every other kind refused it.

## Quick example

```python
import seared as s

@s.seared
class Row(s.Seared):
    name: str = s.Str(required=True)
    score: int = s.Int(required=True)

rows = [Row(name='alice', score=90), Row(name='bob', score=85)]
text = Row.to_csv(rows)
# name,score
# alice,90
# bob,85

loaded = Row.from_csv(text)
loaded == rows                # → True
```

`from_csv` accepts a path-like or a string of CSV content (see
[`_common.md`](_common.md)).

A bad record names its index among the data rows, 0-based with the header
not counted, so `Row[2].score` is the third data row, line 4 of the file:

```python
Row.from_csv('name,score\nalice,90\nbob,85\ncarol,lots\n')
# ValidationError: Row[2].score: cannot deserialize 'lots' as int
```

`to_csv` does the same with the index into the records you passed.
