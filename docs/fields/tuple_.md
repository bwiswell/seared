# `tuple_.py` — `Tuple`

```python
point: tuple = s.Tuple(s.Float(), s.Float(), required=True)
```

Fixed-arity heterogeneous tuple — each position has its own field type,
passed positionally, one per slot. Wire form is a JSON list of the same
length. Variable-length / homogeneous lists belong on `s.Str(many=True)`
etc.

- **Strict mode** refuses anything but a list or tuple, and a length
  other than the slot count (`tuple length mismatch: expected 2, got 1`).
  A slot's failure names its index in the path (`Cls.point[1]: …`).
- **Lax mode** skips both checks and pairs slots with values as `zip`
  does, so a short value gives a short tuple and extra values are
  dropped.

The `format=` carrier hint reaches every slot: under
`Cls.dump(obj, format='msgpack')` a `Bytes` slot carries raw bytes, as a
top-level `Bytes` does, and a `T` slot passes the hint on to its class.
Until 0.4.0 the slots never got it, so a `Bytes` slot stayed base64 under
msgpack. Payloads written that way still load, since `Bytes` reads either
form under any carrier.
