# `tuple.py` — `Tuple`

```python
point: tuple = s.Tuple(items=(s.Float(), s.Float()), required=True)
```

Fixed-arity heterogeneous tuple — each position has its own field type.
Wire form is a JSON list of the same length. Variable-length /
homogeneous lists belong on `s.Str(many=True)` etc.

The `format=` carrier hint reaches every slot: under
`Cls.dump(obj, format='msgpack')` a `Bytes` slot carries raw bytes, as a
top-level `Bytes` does, and a `T` slot passes the hint on to its class.
Until 0.4.0 the slots never got it, so a `Bytes` slot stayed base64 under
msgpack. Payloads written that way still load, since `Bytes` reads either
form under any carrier.
