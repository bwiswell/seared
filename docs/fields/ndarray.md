# `ndarray.py` — `NDArray`

```python
samples: 'np.ndarray' = s.NDArray(required=True)
frame: 'np.ndarray' = s.NDArray(dtype='float32', required=True)
```

`numpy.ndarray` ↔ nested lists: `dump` writes `value.tolist()`, and `load`
reads `np.array(value)`. Requires the optional `numpy` extra
(`uv add 'seared[numpy]'`).

- **The shape survives; the dtype needs declaring.** The lists carry the
  shape, but without a `dtype` `load` infers one from the values, so a
  `float32` array comes back `float64` and an int array `int64`. Declare
  `dtype=` and it comes back as declared (0.4.1).
- **`format=` is ignored.** The wire form is nested lists under every
  carrier, msgpack included.
- A strict `dump` refuses a value that isn't an `ndarray`. Without a
  `dtype`, `load` takes whatever `np.array` accepts.

## Options

| Option | Default | |
|---|---|---|
| `dtype` | `None` | The element type, as anything `numpy.dtype()` accepts (`'float32'`, `np.int32`, `bool`), resolved when the field is built; one it doesn't know is a `TypeError`. `None` infers it from the values. |

## With a `dtype`

`load` casts to it, and a strict `dump` checks against it:

| | Strict | Lax |
|---|---|---|
| `load` | casts only what it can carry over whole (below) | casts as numpy casts |
| `dump` | refuses an array of another dtype | casts it first |

A strict load follows the scalar fields' rules, element by element:

- **A `bool` isn't a number:** an array of bools is refused for an integer
  or float dtype.
- **An integer dtype** takes only integral, finite values within its range:
  `1.5`, `nan` and `300` (for `int8`) are refused.
- **A float dtype** takes any number, narrowing the precision (`float64`
  to `float32` is the point of declaring it), but a finite value that would
  overflow to infinity is refused. Infinity and `nan` stay what they are.
- **A `bool` dtype** takes only `0` and `1`.
- **Numeric strings** cast, as the scalar fields take them; other strings,
  and nesting that isn't rectangular, are refused.

The error names the element: `Samples.values[1][2]: cannot deserialize 1.5
as int32`. The checks see the array numpy builds, not each element, so a
`True` among numbers has already become a `1`.

A `float32` array that goes out and comes back is exactly what it was: its
values are written as the floats they hold, and cast back to `float32`.

## Wire form

```json
[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
```

The dtype isn't on the wire: the field declares it, and both ends read the
same declaration. A self-describing `{shape, dtype, data}` envelope would be
an opt-in `encoding=` of its own, and waits for a consumer that needs it.
