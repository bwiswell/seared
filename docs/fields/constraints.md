# `constraints.py` — bounds on `Int` and `Float`

```python
@s.seared
class Sampling(s.Seared):
    interval_s: float = s.Float(ge=5, le=3600, default=60.0)
    retries: int = s.Int(ge=0, lt=10, default=3)
    gains: list[float] = s.Float(gt=0, many=True, default_factory=list)

Sampling.load({'interval_s': 2})
# ValidationError: Sampling.interval_s: must be >= 5, got 2.0
```

`Int` and `Float` take bounds on their values. New in 0.4.4. Each bound is
declared once and read three times: `load` and `dump` check it,
[`json_schema`](../doc/json_schema.md) writes it as its keyword, and the
generated docs pages show it.

## The options

| Option | A value must be | JSON Schema |
|---|---|---|
| `ge=` | `>=` the bound | `minimum` |
| `gt=` | `>` the bound | `exclusiveMinimum` |
| `le=` | `<=` the bound | `maximum` |
| `lt=` | `<` the bound | `exclusiveMaximum` |

A field takes at most one lower bound (`ge` or `gt`) and one upper (`le` or
`lt`). An `Int`'s bounds are `int`s; a `Float`'s are finite numbers, an
`int` included. Neither takes a `bool`.

## Where they're checked

- **After coercion.** A strict `load` still reads a numeric string or an
  integral float as it always has (a topic capture is a string), then
  checks the number it got.
- **On a strict `dump` too,** as the type is. Construction checks nothing,
  as it checks no types, so `Sampling(retries=-1)` builds, and its `dump`
  raises `Sampling.retries: must be >= 0, got -1`.
- **On each element** of a `many` or `keyed` field, whose index or key
  joins the path: `Sampling.gains[1]: must be > 0, got 0.0`. A `Tuple` slot
  checks its own.
- **Not in lax mode.** A `@s.seared(validate=False)` class skips them, as
  it skips a `Tuple`'s length check: a bound can be refused but not
  coerced.

The message names the first bound a value fails, `must be >= 5, got 2.0`,
with the location in front as for any field's error (see
[`../_core/errors.md`](../_core/errors.md)).

## `NaN` and infinity

A bounded `Float` refuses `NaN`, which fails every comparison, so it fails
every bound, as it does in JSON Schema (`NaN` isn't a JSON number). An
infinity passes a lower bound and fails an upper one. An unbounded `Float`
takes both, as it always has; JSON can't carry either, but msgpack and a
numeric string (`'nan'`, `'inf'`) can.

## Declarations that can't hold

Each raises `TypeError` where the field is declared, usually at import:

| Declaration | Raises |
|---|---|
| `s.Int(ge=0.5)` | `Int: ge= takes an int, got 0.5` |
| `s.Float(le=float('inf'))` | `Float: le= takes a finite number, got inf` |
| `s.Int(ge=0, gt=0)` | `Int: ge= and gt= both set a lower bound; keep one` |
| `s.Int(ge=5, le=1)` | `Int: ge=5 and le=1 leave no value` |
| `s.Int(ge=0, default=-1)` | `Int: default -1 fails its constraints: must be >= 0, got -1` |

A static `default` has to pass, each element of a `many` or `keyed` one
included: an absent key takes the default without being loaded, so a bad
one would reach the object unchecked. A `default_factory` isn't called to
check it.

## In the schema and the docs

`json_schema` and `field_schema` write each bound as its keyword, in both
modes, on the element's schema, so it lands in `items` for a `many` field
and in `additionalProperties` for a `keyed` one:

```json
"retries": {"type": "integer", "minimum": 0, "exclusiveMaximum": 10, "default": 3},
"gains": {"type": "array", "items": {"type": "number", "exclusiveMinimum": 0}}
```

`seared.doc` gives the field's `FieldDoc` a `constraints` tuple,
`(('ge', 0), ('lt', 10))`, and its page's notes say
``bounds: `>= 0`, `< 10` ``.

A subclass of `Int` or `Float` takes the same options and is described by
them, which an override that checks more can't be (see
[`kind.md`](kind.md)).

## The accelerator

A class with a bounded field keeps the pure-Python path for now, whatever
its other fields:

```python
>>> Sampling.__seared_accel__.reason
'Sampling.interval_s: Float with ge= is not accelerated yet'
```

A backend built for `SPEC_ABI` 2, `rusted` 0.4.0 among them, doesn't know
the options, and would check the type but skip the bound. The spec an
unbounded field emits is unchanged. See
[`../_core/accel.md`](../_core/accel.md).

## For tooling

```python
from seared.fields.constraints import OPTIONS, SYMBOLS, declared_constraints

declared_constraints(s.Int(lt=10, ge=0))   # {'ge': 0, 'lt': 10}
declared_constraints(s.Str())              # {}
SYMBOLS['ge']                              # '>='
```

`declared_constraints(field)` gives the options a field sets, in
`OPTIONS` order whatever the declaration's, and is empty for any field
without them. The JSON Schema emitter, `seared.doc` and the accelerator
all read it.
