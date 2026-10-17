# `ndarray.py` — `NDArray`

```python
samples: 'np.ndarray' = s.NDArray(required=True)
```

`numpy.ndarray` ↔ nested lists: `dump` writes `value.tolist()`, and `load`
reads `np.array(value)`. Requires the optional `numpy` extra
(`uv add 'seared[numpy]'`).

- **The shape survives; the dtype doesn't.** The lists carry the shape,
  and `load` infers the dtype from the values, so a `float32` array comes
  back `float64` and an int array `int64`. Cast after loading when the
  dtype matters.
- **`format=` is ignored.** The wire form is nested lists under every
  carrier, msgpack included.
- A strict `dump` refuses a value that isn't an `ndarray`. `load` takes
  whatever `np.array` accepts.

## Wire form

```json
[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
```
