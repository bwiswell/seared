# seared for configuration

seared isn't a configuration library, but a config file is a wire dict
like any other, and a `@s.seared` class reads one with `from_toml`,
`from_json` or `from_yaml`. This page collects what a config needs.

## A config class

Declare it like any class, and add `unknown='raise'`:

```python
import seared as s

@s.seared(unknown='raise')
class Latest(s.Seared):
    key: list[str] = s.Str(many=True, default_factory=list)
    retention: str | None = s.Str(default=None)

@s.seared(unknown='raise')
class Stream(s.Seared):
    cls: str = s.Str(required=True)
    retention: str | None = s.Str(default=None)
    latest: Latest | None = s.T(Latest, default=None)

@s.seared(unknown='raise')
class Config(s.Seared):
    identity: str = s.Str(required=True)
    db_path: str = s.Str(default='chronicle.db')
    streams: list[Stream] = s.T(Stream, many=True, default_factory=list)

cfg = Config.from_toml('stored.toml')
```

## Refuse unknown keys

Without `unknown='raise'`, a misspelt key is dropped without a word, and
its setting keeps its default: a `retension = "7d"` under `[[streams]]`
leaves the stream with no retention at all. With it, `from_toml` raises at
the first typo, in the file's order, and names the rest:

```text
ValidationError: Config.idnetity: unknown key (1 more: streams[0].retension)
```

The refusal covers the whole file, nested sections included, whatever the
nested classes declare: the decision is the outermost load's. Marking the
section classes `unknown='raise'` too makes them refuse when they're
loaded on their own.

A wire message must **not** refuse: an older subscriber reads a newer
publisher's payload by ignoring the fields it doesn't know yet. Keep
`unknown='raise'` for configs and other hand-written input. Where one
class is both, leave the class lenient and refuse per call:
`Cls.from_toml(path, unknown='raise')`.

To report rather than raise, say in a `validate` command that lists every
problem, call `s.unknown_keys(Config, data)`, which returns each unknown
key's path. See [`../_core/unknown.md`](../_core/unknown.md).

## Defaults and `null`

- **Optional settings** are `X | None` with `default=None`; a setting with a
  real default (`port: int = s.Int(default=7447)`) stays `X`.
- **A `null` reads as absent** (since 0.4.0), so it takes the default. Only
  a `nullable=True` field keeps `None`. YAML's `~` is a `null`; TOML has
  none.
- **Required settings** are `required=True`. A refusing load reports a
  misspelt required key as unknown, which says why it's missing.

## What seared leaves to you

- **Environment variables.** seared reads a file or a string, not the
  environment. Layering `ENV_VAR` overrides on a file is a few lines in
  the consumer: read the file to a dict, update it from the environment,
  then `Config.load(data)`.
- **Searching for the file.** `from_toml(source)` takes a path or the TOML
  text itself (see [`../formats/_common.md`](../formats/_common.md)), and
  nothing else.
- **Validating across fields.** A `__post_init__` raising
  `ValidationError` runs on every load (see
  [`../_core/errors.md`](../_core/errors.md)).
