# `fields/polars_.py` — `PolarsFrame` field

Tabular data backed by `polars.DataFrame`. Lives behind the optional
`seared[polars]` extra. Mirrors [`PandasFrame`](pandas_.md) — same
wire shape, swap the import and field type.

## Quick example

```python
import polars as pl
import seared as s

@s.seared
class Report(s.Seared):
    name: str          = s.Str(required=True)
    data: pl.DataFrame = s.PolarsFrame(required=True)

r = Report(name='r1', data=pl.DataFrame({'a': [1, 2], 'b': [3, 4]}))
encoded = Report.to_json(r)
loaded = Report.from_json(encoded)
loaded.data.equals(r.data)      # → True
```

## Wire shape

`[{col: val, ...}, ...]` — polars `to_dicts()` produces it; the
`polars.DataFrame(records)` constructor consumes it. Empty inputs are
handled specially (an empty list builds an empty `pl.DataFrame()` to
sidestep the schema-required warning).

**Tradeoff:** identical to [`PandasFrame`](pandas_.md) — record form
loses dtype information for anything JSON can't represent.

## What's not supported

- **`many=True` / `keyed=True`** — a `PolarsFrame` field is one frame.
  Wrap in a `T(SomeWrapperClass)` if you need a list-of-frames.
- **Binary wire form** (Parquet / Arrow IPC). Records-as-JSON is the
  only wire shape today.

## Missing-extra behaviour

When you `import seared` without polars installed, `s.PolarsFrame` is
a placeholder class that raises `ImportError` at construction time:

```
ImportError: seared.PolarsFrame requires polars. Install it with: uv add 'seared[polars]'
```
