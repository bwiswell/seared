# `bool.py` — `Bool`

```python
flag: bool = s.Bool(default=False)
```

Python `bool` ↔ JSON `true` / `false`. Strict on serialize (`validate=True`
raises on non-bool); permissive on deserialize.

Deserialize reads the usual spellings in both modes, after `strip()` /
`lower()`: `true` / `1` / `yes` / `on` → `True`, and `false` / `0` / `no` /
`off` → `False`. Beyond those:

| Input | `validate=True` | `validate=False` |
|-------|-----------------|------------------|
| any other string | raises `ValidationError` | truthiness (`'maybe'` → `True`, `''` → `False`) |
| `0` / `1` | `False` / `True` | `False` / `True` |
| any other `int` | raises `ValidationError` | truthiness (`2` → `True`) |
| anything else | raises `ValidationError` | truthiness |

Strict mode takes the ints `0` and `1` only, as its string table takes
`'0'` and `'1'` but not `'2'`; until 0.4.0 it read any int as its
truthiness.

Before 0.3.3, lax mode skipped the spellings and went straight to
truthiness, so `'false'` loaded as `True`. Accelerator backends built against
`SPEC_ABI` 1 still do. seared 0.3.3 and its patches kept a lax class with a
`Bool` off the accelerator for that reason; from 0.4.0, which needs a
`SPEC_ABI` 2 backend, it accelerates again (see
[`../_core/accel.md`](../_core/accel.md)).
