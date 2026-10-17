# `_core/unknown.py` — unknown keys

A key in a wire dict that its class doesn't declare is an *unknown* key.
`load` ignores them by default. 0.4.1 adds a report of them, and an opt-in
refusal.

```python
@s.seared
class Cfg(s.Seared):
    n: int = s.Int(default=0)

Cfg.load({'n': 2, 'nn': 3})                     # Cfg(n=2): `nn` is dropped
s.unknown_keys(Cfg, {'n': 2, 'nn': 3})          # [('nn',)]
Cfg.load({'n': 2, 'nn': 3}, unknown='raise')    # ValidationError: Cfg.nn: unknown key
```

## Why the default ignores them

On the wire, ignoring is load-bearing. A subscriber on an older version
reads a newer publisher's payload by ignoring the fields it doesn't know
yet, which is how the family removes or adds a field without a lockstep
upgrade. So `'ignore'` stays the default, and the refusal is **never for
a wire message**.

For a config file, or any input a person or an agent wrote, ignoring
hides a typo instead: the misspelt key is dropped, and its setting keeps
its default without a word. That's what the refusal is for. See
[`../overview/configuration.md`](../overview/configuration.md).

## `unknown_keys(cls, data)`

```python
s.unknown_keys(Cls, data) -> list[tuple[str | int, ...]]
```

The path of every unknown key in `data`, depth-first, in the input's
order; empty when every key is known. Paths use `load`'s vocabulary (wire
keys, list indices, keyed-dict keys), so `functools.reduce(operator.getitem,
path, data)` retrieves the value under each.

It's a report: it never raises for what `data` holds, and never changes
it. Data that isn't a dict has nothing to report, since `load` refuses it
on its own. A class that isn't `@seared` raises `TypeError`.

## What counts as known

At each level:

- each declared field's **wire key** (`data_key` when set, so the
  attribute name is unknown if it differs);
- each `Union` envelope's `tag_key`, and its `payload_key` or, in a flat
  envelope, the selected variant's own keys.

Below a declared field the walk descends into `T` targets (element by
element for `many`, value by value for `keyed`) and into `Tuple` slots.
`Dict` values, arrays and frames are data rather than schema, so their
keys are never reported. A `null` value isn't walked.

Two places can't be accounted for, and report nothing:

- **a payload routed to a `fallback=` variant.** The fallback exists to
  accept a variant this version doesn't know, so its keys can't be
  checked against anything;
- **a flat envelope whose tag is missing or unknown.** Its variant's keys
  sit beside the parent's, and no declared variant says which they are.
  `load` refuses the tag with its own error.

## The `unknown=` option

`'ignore'` or `'raise'`. Anything else is a `ValueError`.

| Where | Meaning |
|---|---|
| `@s.seared(unknown='raise')` | The class's default: every `load`, `loads` and `from_*` of it refuses. Recorded on `Cls.__seared_unknown__` |
| `Cls.load(data, unknown=…)`, `Cls.loads(text, unknown=…)` | This call only; `None` (the default) takes the class's |
| `Cls.from_json` / `from_toml` / `from_yaml` / `from_csv(source, unknown=…)` | The same, for a file or string. In CSV an extra column is an unknown key |

A refusing load raises **one** `ValidationError` for every unknown key:
its `path` is the first's, and its reason counts and names the rest (up
to five), so a config with three typos is fixed in one pass:

```text
Config.idnetity: unknown key (2 more: streams[0].retension, streams[1].clss)
```

### Before the load, and over the whole input

The refusal walks the input **before** the class's own load runs. Two
things follow:

- **It reports the cause.** A misspelt required key reads
  `retension: unknown key`, not `required key missing`.
- **A compiled load is untouched.** The walk is Python, in front of
  whichever load the class has, so a refusing class stays accelerated
  and raises exactly what the pure-Python class does. `rusted` never
  sees the option, and the plain-data spec doesn't change.

The walk covers every level of the input, so the decision is the
outermost load's. A nested class's own `unknown=` governs only a load of
that class itself: inside another class's load, a `T` or a `Union` calls
its bare load (`Cls.__seared_load__`, internal), with no option in front.
That's also what lets a refusing class be a flat `Union` variant, whose
payload carries its parent's keys.

## Internals

- `refuse_unknown_keys(cls, data)` — the refusal itself, raising as above.
- `check_unknown(value, where)` — refuses a value that isn't `'ignore'` or
  `'raise'`, naming the caller (`@seared`, `Cfg.load`).
- `type Unknown = Literal['ignore', 'raise']` — the option's type.

`s.unknown_keys` is the public name; the rest are reached through the
option.
