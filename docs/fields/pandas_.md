# `fields/pandas_.py` — `PandasFrame` field

Tabular data backed by `pandas.DataFrame`. Lives behind the optional
`seared[pandas]` extra.

## Quick example

```python
import pandas as pd
import seared as s

@s.seared
class Report(s.Seared):
    name: str          = s.Str(required=True)
    data: pd.DataFrame = s.PandasFrame(required=True)

r = Report(name='r1', data=pd.DataFrame({'a': [1, 2], 'b': [3, 4]}))
encoded = Report.to_json(r)
loaded = Report.from_json(encoded)
loaded.data.equals(r.data)      # → True
```

## Wire shape

`[{col: val, ...}, ...]` — pandas `to_dict('records')` produces it,
`DataFrame.from_records` consumes it. Matches the JSON-records form
most JSON consumers expect; round-trips cleanly through
`to_json` / `from_json`.

**Tradeoff:** records form loses dtype information for anything JSON
can't represent (datetime, Categorical, timezone-aware timestamps,
nullable integers, etc.). Round-trip is lossy for those columns. For
dtype-preserving wire transport, layer your own Arrow / Parquet codec
on top — out of scope for this field.

## What's not supported

- **`many=True` / `keyed=True`** — a `PandasFrame` field is one frame.
  Wrap in a `T(SomeWrapperClass)` if you need a list-of-frames.
- **Binary wire form** (Parquet / Arrow IPC). Records-as-JSON is the
  only wire shape today.
- **Cross-backend polymorphism.** `PandasFrame` and
  [`PolarsFrame`](polars_.md) are distinct types; pick one per field.
  Prevents the "two backends installed, which wins?" question.

## Missing-extra behaviour

When you `import seared` without pandas installed, `s.PandasFrame` is
a placeholder class that raises `ImportError` only at construction
time. So `import seared as s` always works; `s.PandasFrame()` without
pandas raises a helpful error:

```
ImportError: seared.PandasFrame requires pandas. Install it with: uv add 'seared[pandas]'
```

Mirrors the [`NDArray`](ndarray.md) and [`PolarsFrame`](polars_.md)
patterns.
