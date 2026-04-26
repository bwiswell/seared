# `tuple.py` — `Tuple`

```python
point: tuple = s.Tuple(items=(s.Float(), s.Float()), required=True)
```

Fixed-arity heterogeneous tuple — each position has its own field type.
Wire form is a JSON list of the same length. Variable-length /
homogeneous lists belong on `s.Str(many=True)` etc.
