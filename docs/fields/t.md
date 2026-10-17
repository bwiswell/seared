# `t.py` — `T`

```python
@s.seared
class Inner(s.Seared):
    value: int = s.Int(required=True)

@s.seared
class Outer(s.Seared):
    nested: Inner = s.T(Inner, required=True)
```

Embeds another seared class as a field. The wire form is the inner
class's `dump` output (a nested dict). On `load`, dispatches to the
inner class's own load, `Inner.__seared_load__`, with no `unknown=` in
front of it: inside another class's load, unknown keys are the outermost
load's to refuse, and its walk covers this subtree (see
[`../_core/unknown.md`](../_core/unknown.md)). So `Inner`'s own
`unknown='raise'` applies when `Inner` is loaded by itself.

Supports `many=True` and `keyed=True` for lists / maps of nested
instances.

The `format=` carrier hint crosses the nesting boundary: `Outer.dump(obj,
format='msgpack')` reaches a `Bytes` inside `Inner` exactly as it would at
the top level. (`Union` threads it to its variant the same way.)
