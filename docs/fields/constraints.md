# `constraints.py` — bounds, lengths and patterns

```python
@s.seared
class Sampling(s.Seared):
    interval_s: float = s.Float(ge=5, le=3600, default=60.0)
    retries: int = s.Int(ge=0, lt=10, default=3)
    gains: list[float] = s.Float(gt=0, many=True, default_factory=list)

@s.seared
class Account(s.Seared):
    handle: str = s.Str(min_length=3, max_length=32, pattern=r'^[a-z0-9_]+$', required=True)

Sampling.load({'interval_s': 2})
# ValidationError: Sampling.interval_s: must be >= 5, got 2.0
Account.load({'handle': 'Ana Lee'})
# ValidationError: Account.handle: must match the pattern '^[a-z0-9_]+$'
```

`Int` and `Float` take bounds; `Str` takes lengths and a pattern. New in
0.4.4. Each is declared once and read three times: `load` and `dump` check
it, [`json_schema`](../doc/json_schema.md) writes it as its keyword, and the
generated docs pages show it.

## The options

| Field | Option | A value must | JSON Schema |
|---|---|---|---|
| `Int`, `Float` | `ge=` | be `>=` the bound | `minimum` |
| | `gt=` | be `>` the bound | `exclusiveMinimum` |
| | `le=` | be `<=` the bound | `maximum` |
| | `lt=` | be `<` the bound | `exclusiveMaximum` |
| `Str` | `min_length=` | be at least that long | `minLength` |
| | `max_length=` | be at most that long | `maxLength` |
| | `pattern=` | contain a match for the pattern | `pattern`, as declared |

A field takes at most one lower bound (`ge` or `gt`) and one upper (`le` or
`lt`). An `Int`'s bounds are `int`s; a `Float`'s are finite numbers, an
`int` included. Neither takes a `bool`. A length is a non-negative `int`,
counted in code points, as JSON Schema counts characters: an emoji is one,
where JavaScript's `.length` says two. A pattern is a `str` within the
portable subset ([Patterns](#patterns)).

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
  it skips a `Tuple`'s length check: a value can be refused but not coerced
  into range.

The message names the first check a value fails, with the location in
front as for any field's error (see [`../_core/errors.md`](../_core/errors.md)):
`must be >= 5, got 2.0`, `must be at least 3 characters long, got 2`, or
`must match the pattern '^[a-z0-9_]+$'`. A `Str` checks its lengths before
its pattern. A pattern's message never shows the value: a pattern most
often guards the shape of a name, and the value that fails one is the
likeliest to be a secret pasted in its place.

## `NaN` and infinity

A bounded `Float` refuses `NaN`, which fails every comparison, so it fails
every bound, as it does in JSON Schema (`NaN` isn't a JSON number). An
infinity passes a lower bound and fails an upper one. An unbounded `Float`
takes both, as it always has; JSON can't carry either, but msgpack and a
numeric string (`'nan'`, `'inf'`) can.

## Patterns

A pattern is JSON Schema's: an ECMA-262 regex, searched for rather than
anchored. `[0-9]` passes `'room 101'`, and `^...$` anchors a pattern to the
whole string.

Python's `re` reads some regexes differently from ECMA-262. `$` matches
before a final newline in Python and not in ECMA-262; `.` matches `\r`,
U+2028 and U+2029 in Python and not in ECMA-262; `\d` and `\w` take any
Unicode digit or letter in Python and ASCII alone in ECMA-262. And each
engine refuses, or warns on, some regexes the other takes. So seared takes
only a pattern within the subset both read the same way, and checks a
translation of it: outside a class, `$` becomes `\Z`, and `.` a class that
leaves out the four line terminators (`\n`, `\r`, U+2028 and U+2029). The
schema gets the pattern as declared, so a JavaScript validator and `load`
agree on every value.

### The portable subset

| Construct | Written as |
|---|---|
| A character | itself; `\` before a syntax character (`^ $ \ . * + ? ( ) [ ] { } \| /`), or before `-` inside a class; `\n`, `\r`, `\t`, `\f`, `\v`; `\xHH`; `\uHHHH` outside the surrogates |
| Anchors and any character | `^`, `$`, `.` |
| Groups | `(...)`, `(?:...)`, the lookaheads `(?=...)` and `(?!...)`, and `\|` between alternatives |
| Classes | `[...]` and `[^...]`, with ranges. A `]` can't come first, a `[` can't appear, nor a doubled `&&`, `\|\|` or `~~`, and a bare `-` only starts or ends one |
| Quantifiers | `*`, `+`, `?`, `{n}`, `{n,}` and `{n,m}`, each optionally lazy (`?`), after something they can repeat: never an assertion (`^`, `$`, a lookahead) |

### What to write instead

| Not portable | Write |
|---|---|
| `\d`, `\D` | `[0-9]`, `[^0-9]` |
| `\w`, `\W` | `[A-Za-z0-9_]`, `[^A-Za-z0-9_]` |
| `\s`, `\S` | the whitespace you mean, as a class: `[ \t\n\r]` |
| `\A`; `\Z`, `\z` | `^`; `$` |
| `{,n}` | `{0,n}` |
| `\0` | `\x00` |
| `\u{…}`, a surrogate, or a pair of them | the character itself, or `\uHHHH` |
| `\-` outside a class, `\:` and any other escape | the character itself |
| a literal `{`, `}` or `]` | `\{`, `\}`, `\]` |
| a class opening with `]`, a `[` inside one | `\]`, `\[` |
| `\b`, `\B`, backreferences, named groups, lookbehind, inline flags, atomic groups, possessive quantifiers, a repeated assertion | no portable form |

A refusal is a `TypeError` where the field is declared, naming the
construct, where it is, and its portable spelling where there is one:

```python
s.Str(pattern=r'^\d{4}$')
# TypeError: Str: pattern='^\\d{4}$': \d at 1 isn't portable; write [0-9]
s.Str(pattern=r'(?<=a)b')
# TypeError: Str: pattern='(?<=a)b': (?<= at 0 isn't portable (lookbehind)
```

A compiled `re.Pattern` is refused too, since its flags have no JSON Schema
form. Every rule above comes from running both engines: seared's tests hold
it to the verdicts of `new RegExp(pattern, 'u')`, which is how JSON Schema
validators compile a pattern, over a corpus of the subset and its
refusals.

## Declarations that can't hold

Each raises `TypeError` where the field is declared, usually at import:

| Declaration | Raises |
|---|---|
| `s.Int(ge=0.5)` | `Int: ge= takes an int, got 0.5` |
| `s.Float(le=float('inf'))` | `Float: le= takes a finite number, got inf` |
| `s.Int(ge=0, gt=0)` | `Int: ge= and gt= both set a lower bound; keep one` |
| `s.Int(ge=5, le=1)` | `Int: ge=5 and le=1 leave no value` |
| `s.Str(min_length=-1)` | `Str: min_length= takes a non-negative int, got -1` |
| `s.Str(min_length=5, max_length=3)` | `Str: min_length=5 and max_length=3 leave no value` |
| `s.Str(pattern='a{,3}')` | `Str: pattern='a{,3}': {,3} at 1 isn't portable; write {0,3}` |
| `s.Int(ge=0, default=-1)` | `Int: default -1 fails its constraints: must be >= 0, got -1` |
| `s.Str(pattern='^[a-z]+$', default='A')` | `Str: default 'A' fails its constraints: must match the pattern '^[a-z]+$'` |

A static `default` has to pass, each element of a `many` or `keyed` one
included: an absent key takes the default without being loaded, so a bad
one would reach the object unchecked. A `default_factory` isn't called to
check it.

## In the schema and the docs

`json_schema` and `field_schema` write each constraint as its keyword, in
both modes, on the element's schema, so it lands in `items` for a `many`
field and in `additionalProperties` for a `keyed` one:

```json
"retries": {"type": "integer", "minimum": 0, "exclusiveMaximum": 10, "default": 3},
"gains": {"type": "array", "items": {"type": "number", "exclusiveMinimum": 0}},
"handle": {"type": "string", "minLength": 3, "maxLength": 32, "pattern": "^[a-z0-9_]+$"}
```

`seared.doc` gives the field's `FieldDoc` a `constraints` tuple,
`(('ge', 0), ('lt', 10))`, and its page's notes say
``bounds: `>= 0`, `< 10` ``, `length: 3 to 32` and
``pattern: `^[a-z0-9_]+$` ``.

A subclass of `Int`, `Float` or `Str` takes the same options and is
described by them, which an override that checks more can't be (see
[`kind.md`](kind.md)).

## The accelerator

A class with a constrained field keeps the pure-Python path for now,
whatever its other fields:

```python
>>> Sampling.__seared_accel__.reason
'Sampling.interval_s: Float with ge= is not accelerated yet'
>>> Account.__seared_accel__.reason
'Account.handle: Str with min_length= is not accelerated yet'
```

A backend built for `SPEC_ABI` 2, `rusted` 0.4.0 among them, doesn't know
the options, and would check the type but skip the constraint. The spec an
unconstrained field emits is unchanged. See
[`../_core/accel.md`](../_core/accel.md).

## For tooling

```python
from seared.fields.constraints import OPTIONS, SYMBOLS, declared_constraints, portable_regex

declared_constraints(s.Int(lt=10, ge=0))           # {'ge': 0, 'lt': 10}
declared_constraints(s.Str(pattern='^a', max_length=4))  # {'max_length': 4, 'pattern': '^a'}
declared_constraints(s.Str())                      # {}
SYMBOLS['ge']                                      # '>='
portable_regex(r'^[a-z]+$')                        # the compiled translation seared checks with
```

`declared_constraints(field)` gives the options a field sets, in `OPTIONS`
order whatever the declaration's, and is empty for any field without them.
The JSON Schema emitter, `seared.doc` and the accelerator all read it.
`portable_regex(pattern)` compiles a pattern as a `Str` does, raising the
same `TypeError` for one outside the subset.
