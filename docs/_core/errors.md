# `_core/errors.py` — exception hierarchy

```
ValueError                       # stdlib
└── SearedError                  # seared base; not raised directly
    └── ValidationError          # type / shape mismatch on load or dump
```

Both exceptions are re-exported at the package root: `s.SearedError`,
`s.ValidationError`.

## When each is raised

`ValidationError` is the only concrete error seared raises today.
Sources:

- **`load`** — required field absent; type mismatch on a wire value;
  unknown `Union` tag without a `default=` fallback; CSV/Pandas/Polars
  shape mismatches.
- **`dump`** — strict `validate=True` produces a `ValidationError`
  when an instance attribute doesn't match the declared field type.

`SearedError` is the catch-all base — handy for `except SearedError:`
without naming `ValidationError` directly. Future error types (for
codec failures, schema-version mismatches, etc.) would extend
`SearedError` rather than `ValidationError`.

## Where it happened (0.4.0)

A `ValidationError` carries its location as parts, and its message is
built from them:

| Attribute | Holds |
|---|---|
| `reason` | What went wrong: `cannot deserialize 'x' as int` |
| `path` | Where, as a tuple of keys and indices: `('items', 1, 'n')` |
| `cls_name` | The outermost class whose `load` or `dump` it passed through, or `None` |

```python
>>> Outer.load({'items': [{'n': 1}, {'n': 'x'}]})
ValidationError: Outer.items[1].n: cannot deserialize 'x' as int
```

**The path addresses what the caller passed in.** On `load` it holds wire
keys (a field's `data_key` where it has one), list indices and keyed-dict
keys, so it retrieves the offending value from the input:

```python
>>> functools.reduce(operator.getitem, err.path, data)
'x'
```

On `dump` the input is the object, so the path holds attribute names. A few
cases worth knowing:

- **A missing required key** ends the path at the key that is absent:
  `Outer.items[0].n: required key missing`. Looking that one up raises
  `KeyError`, which is the point.
- **A non-dict** names the class alone: `Outer: expected dict, got list`.
- **A `Union`'s** tag errors point at the tag key. A nested envelope's
  payload errors sit under its `payload_key`; a flat envelope's are at the
  parent's own keys, because that's where its fields live.
- **A `Tuple` slot** adds its index: `Outer.pair[1]`.
- **`from_csv` / `to_csv`** add the record's index among the data rows,
  0-based with the header not counted: `Row[2].id` is `rows[2]['id']`, not
  line 3 of the file.
- **A `ValidationError` raised in a `__post_init__`** names the object it
  belongs to: `Plan.windows[1]: window ends before it starts`. Any other
  exception passes through untouched.

**How it renders:** a key that is a Python identifier reads as `.name`, any
other as `['key']`, and an index as `[i]`. So
`Outer.readers['r-1'].port`. With an empty path the message is
`Outer: reason`; with no class, as when a field's `deserialize` is called
directly, it is the bare reason.

**Fail-fast.** A `load` stops at the first error, so there is one location,
not a list.

**Constructing one** still works with a single argument,
`ValidationError('reason')`, which has no path and no class until a `load`
or `dump` adds them. A custom field can raise it exactly as before.

**Pickling** keeps all three parts, so an error crossing a process
boundary (`multiprocessing`, `concurrent.futures`) arrives intact.

Before 0.4.0 the message was the bare reason, except for two that named
their own location: `Outer.n is required` and
`Outer.load expected dict, got list`. They now read
`Outer.n: required key missing` and `Outer: expected dict, got list`. A
regex over the old text should match `err.reason` instead.

## Why `ValueError` as the root

Schema mismatches are conceptually "the value is wrong" — `ValueError`
is the closest stdlib match. Callers that already catch `ValueError`
(common in input-validation pipelines) get seared errors for free
without coupling to `seared.SearedError`.
