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

## Why `ValueError` as the root

Schema mismatches are conceptually "the value is wrong" — `ValueError`
is the closest stdlib match. Callers that already catch `ValueError`
(common in input-validation pipelines) get seared errors for free
without coupling to `seared.SearedError`.
