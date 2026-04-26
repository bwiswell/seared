# `ndarray.py` — `NDArray`

```python
samples: 'np.ndarray' = s.NDArray(required=True)
```

`numpy.ndarray` ↔ JSON-safe shape + dtype + base64 payload (default).
Round-trip preserves shape, dtype, and byte order. Requires the
optional `numpy` extra (`uv add 'seared[numpy]'`).

When the carrier supports raw bytes (`format='msgpack'`), the field
emits native `bytes` for the payload — same shape/dtype envelope, no
base64 overhead.

## Wire form

```json
{
    "shape": [3, 4],
    "dtype": "float64",
    "data": "<base64 or raw bytes>"
}
```
