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
