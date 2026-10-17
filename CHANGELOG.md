# Changelog

Each version of seared, newest first.

A **Breaking** line means code written for the version before may fail, or load differently. A **Fewer classes
accelerate** line means the `rusted` accelerator now declines some classes it used to take: they run on the
pure-Python path, more slowly, and `Cls.__seared_accel__.reason` says why.

The top entry, while it reads *unreleased*, collects what has merged for the next version; each change adds its own
lines as it lands, and the entry is dated when that version is released.

## 0.4.1 — 2026-10-17

**Refusing unknown keys, for config files.** A key a class doesn't declare is still dropped by default, which the
wire depends on, but a class or a call can now refuse it. `seared.doc` gains a coverage check and documents every
class the decorator built, and `NDArray` gains a `dtype`.

### Added

- **`unknown=`, refusing a key a class doesn't declare.** `@s.seared(unknown='raise')` makes it the class's default,
  and `load`, `loads` and the `from_json`, `from_toml`, `from_yaml` and `from_csv` readers take `unknown='ignore'`
  or `'raise'` for one call, `None` meaning the class's own. A refusing load raises one `ValidationError` at the
  first unknown key that names up to five more, and covers the whole input, nested classes included. It runs before
  the load, so a misspelt required key reads as unknown rather than missing, and an accelerated class stays
  accelerated. The default stays `'ignore'`, which a wire message depends on. A class records its option on
  `__seared_unknown__`, and any other value raises `ValueError`.
- **`s.unknown_keys(cls, data)`** reports the path of every unknown key without raising. It walks `T` targets,
  `many` and `keyed` elements, `Tuple` slots and `Union` envelopes, and skips `Dict` values and a payload routed to
  `fallback=`.
- **`--require-docs`**, a flag for `python -m seared.doc`: before writing or checking anything, it lists each field
  without a `doc=` as `module.Class.attr` and fails with exit status 1, so with `--check` CI fails on missing docs
  as well as drift. `seared.doc.undocumented(target)` returns the same list. `python -m zeared.doc` runs the same
  CLI, so it gains the flag with this version.
- **`NDArray(dtype=…)`**, an element type for an array field, as anything `numpy.dtype()` accepts. `load` casts to
  it, so a `float32` array comes back `float32` where it came back `float64`. A strict load casts only what it can
  carry over whole, by the scalar fields' rules: no `bool` for a number, no fractional, non-finite or out-of-range
  value for an integer, no overflow to infinity for a float, and only `0` and `1` for a `bool`. The error names the
  element (`Samples.values[1][2]`). A strict dump refuses an array of another dtype, and a lax one casts it.
  `seared.doc` shows the dtype in the notes column, from a new `FieldDoc.dtype`. An array still declines the
  accelerator, so `rusted` is unaffected.
- **Docs for config files:** `docs/overview/configuration.md`, and `docs/_core/unknown.md` for the new module. The
  README gains *Configuration files*.

### Changed

- A nested `T` or `Union` loads its class through the class's own load, kept as `__seared_load__`, rather than its
  public `load`. So a nested class's `unknown=` applies only when that class is loaded by itself, and each nested
  object skips a call layer.

### Fixed

- **`seared.doc` documents every class the decorator built.** `is_seared_class` asked for the `Seared` base and at
  least one field, so a decorated class without the base (`@zeared` is the same decorator) or a `Union` variant with
  no fields got no page, and a page that linked to it linked to nothing. It now asks only whether `@seared` built
  the class, so a subclass of a decorated class that isn't decorated itself no longer counts, where its inherited
  fields used to give it a page.
- **A class without a docstring stays without one.** `dataclass()` writes its generated signature into `__doc__`
  when a class has none, so `seared.doc` used the signature as the class's summary, on its page and in the index,
  and zeared's TypeScript emitter put it in the class's JSDoc. The decorator now puts the `None` back, so such a
  class's `__doc__` is `None`.

## 0.4.0 — 2026-10-17

**Errors that say where they happened, `null` read as absent, lossless strict coercion, and `SPEC_ABI` 2.**
The breaking release: the README's *Upgrading to 0.4.0* lists every break with what to do.

### Added

- **`CHANGELOG.md`**, this file: every release from 0.1.0 on, newest first. It is kept in the repository and grows
  with each change as it merges, where it had been reconstructed after each release.
- **Errors say where they happened.** A `ValidationError` carries `.reason`, `.path` and `.cls_name`, and its
  message reads `Outer.items[1].n: cannot deserialize 'x' as int`. On `load` the path holds wire keys, list indices
  and keyed-dict keys, so `functools.reduce(operator.getitem, err.path, data)` retrieves the offending value; on
  `dump` it holds attribute names.
  - A missing required key ends the path at the absent key: `Outer.items[0].n: required key missing`.
  - A `Union`'s tag errors point at the tag key, and a nested envelope's payload errors sit under its `payload_key`.
  - A `Tuple` slot adds its index.
  - A `ValidationError` raised in a `__post_init__` names the object it belongs to; any other exception passes
    through untouched.
  - Pickling keeps all three parts.

  A `load` still stops at the first error, and `ValidationError('reason')` still works, with no path or class until
  a `load` or `dump` adds them.
- **`from_csv` and `to_csv` name the bad record** by its 0-based index among the data rows, header not counted:
  `Row[2].id`.
- **`nullable=True`**, a field option that makes `None` a value: `load` keeps a wire `null` as `None`, even over a
  default, and `dump` writes `None` as `null`. It is independent of `required`, as in JSON Schema, so a nullable
  required field must be present but may be `null`. Annotate it `X | None`. Every field takes it except `Union`,
  which refuses it with a `TypeError`, since its envelope has no one key to carry a `null`.
- **`Seared.dumps(obj, **kwargs)`** passes keyword arguments through to `json.dumps`, as `to_json` already did. Pass
  `allow_nan=False` for JSON bound for a browser: by default a `NaN` or infinite float is written as a bare `NaN` or
  `Infinity`, which Python reads back and standard JSON parsers refuse. The default is unchanged.
- **Pages for `seared.doc`** under `docs/doc/` (the CLI, discovery, the public API and the page format), and a
  README *Schema docs* section.

### Changed

- **Fewer classes accelerate:** every class, while `rusted` 0.3.x is the installed backend. seared now emits
  `SPEC_ABI` 2, because 0.4.0 changes what some field kinds mean, and a backend built against 1 would keep the old
  meanings without anyone noticing. So seared declines it, and every class keeps the pure-Python path, which gives
  the new answers. `accel_status()` and `__seared_accel__` say why: the backend
  `declares SPEC_ABI 1; this seared emits 2`. `rusted` 0.4.0 is the matching release.
- **Breaking:** under `SEARED_ACCEL=require`, decorating a class now raises `SearedError` while `rusted` 0.3.x is
  installed, since no backend that matches `SPEC_ABI` 2 loaded. Install `rusted` 0.4.0.
- **Lax `Bool` accelerates again** with a `SPEC_ABI` 2 backend. 0.3.3 fixed lax `Bool` in Python (`'false'` had
  loaded as `True`) and kept every `validate=False` class with a `Bool` off the accelerator until a backend carried
  the fix; ABI 2 does.
- The README installs `rusted` by its `v0.4.0` tag and explains the `SPEC_ABI` handshake, and
  `docs/_core/accel.md` gains a `SPEC_ABI` 2 section.
- **Breaking:** error messages gain their location as a prefix, `Cls.path: reason`. `.reason` keeps each field's
  text word for word, so a pattern written against the old message can match `err.reason` instead. Two messages
  that named their own location are reworded:
  - `Outer.n is required` reads `Outer.n: required key missing`, and names the field by its wire key, its
    `data_key` where it has one, rather than its attribute;
  - `Outer.load expected dict, got list` reads `Outer: expected dict, got list`.

  A field's `deserialize` called on its own still raises the bare reason.
- **`SPEC_ABI` 2's error contract:** a backend constructs the error class the spec carries as
  `error(reason, path=…, cls_name=…)`, and must end with the same three parts as the Python path.
- **Breaking:** a `Union`'s fallback variant is now named with `fallback=`, not `default=`. On every other field,
  `default=` is the value an absent key gets; read that way, `Union(default=Unknown)` would have filled an omitted
  attribute with the class `Unknown` itself. So `default=` (anything but `None`) and `default_factory=` now raise
  `TypeError` pointing at `fallback=`, rather than change meaning silently. `default=None` is still accepted.
- **Breaking:** a wire `null` on a field that isn't nullable reads as an absent key. A required field raises
  `required key missing`, and a defaulted one gets its default, where before the `null` satisfied `required` and
  replaced the default with `None`. `dump` already left `None` out, so seared-to-seared traffic is unchanged; the
  change is for `null`s from elsewhere. The same goes in lax mode, for YAML's `~`, and for the cells `from_csv`
  finds missing in a short row. A `null` element inside a `many` or `keyed` collection is still an error in strict
  mode; lax mode hands it to the field's own coercion, as before.
- A `null` under a `Union`'s `payload_key` is an absent payload, so the variant loads from its defaults rather than
  raising `expected dict, got NoneType`.
- **`to_toml` leaves out `None`-valued keys**, at any depth, since TOML has no null; they read back as absent. A
  `Dict` value of `None` had made `tomli-w` raise.
- **`SPEC_ABI` 2's spec carries `nullable`** for each field.
- **The pure-Python `load` and `dump` make one fewer call per field.** Whether a field is a `Union` envelope is now
  settled once per class, when the class is decorated, rather than asked of every field on every call. Nothing
  else changes, and accelerated classes never ran that code.
- **Breaking:** strict coercion no longer loses data.
  - Strict `Int` refuses a float with a fractional part (`3.7`), which it used to truncate. Integral floats (`3.0`)
    and numeric strings (`'42'`) still load, and lax mode still truncates.
  - Strict `Bool` takes only the ints `0` and `1`, as its string table takes `'0'` and `'1'`; `2` used to load as
    `True`. Lax mode is unchanged.
  - A strict int-valued `Enum` follows strict `Int`: `2.9` and `True` are refused, where they used to load as the
    members for `2` and `1`.
- **Breaking:** `seared.doc`'s fields table follows 0.4.0's rules, so a committed page checked with `--check` fails
  until it is regenerated, which is one command. Three things change, and nothing else on the page:
  - an optional field with no default shows `None` in the `default` column, the value its attribute gets, rather
    than `null`, which such a field never loads or dumps;
  - a nullable field's notes say `nullable: null loads as None`, which its annotation can't show; `FieldDoc` gains a
    `nullable` flag, appended so positional construction still works;
  - a `Union` row is marked required, with no default: a missing or `null` tag always raises.
- **Breaking:** CSV's empty cell is its null. `from_csv` reads an empty cell, like a short row's missing one, as
  `null`, so the field takes its default, a nullable one keeps `None`, and a required one raises
  `required key missing`. It had reached the field as `''`: a `Str` loaded it as `''` and every other kind refused
  it, so an optional `None` couldn't round-trip through CSV. Now one does, for every flat field kind; an empty
  string can't, since it shares the cell with `None`. And `to_csv` gives a `dump=False` field no column, where it
  had written one that was always empty.
- **The docs say what the code does.** `NDArray` is nested lists, its dtype inferred on load and `format=`
  ignored, never the binary envelope they described; `format=` reaches `Bytes`, and `T` and `Tuple` pass it on; a
  lax `null` element is coerced by its field's kind; `SearedError` is raised for accelerator setup. The field pages
  gain what they lacked: the date and time `format=` option, coercion for `Float` and `Str`, an exact `Enum`
  lookup, `Union`'s options.
- The README gains *Upgrading to 0.4.0*, and installs seared by its `v0.4.0` tag.
- **Dependencies:** the dev group's `pytest` range lifts to `>=8.0,<10.0`, and the refreshed lockfile resolves
  pytest 9.1.1, ruff 0.17.1 and ty 0.0.89, and polars 2.0 for the frame tests, which the `polars` extra's `>=1.0`
  already allowed. seared itself still has no runtime dependencies.
- **The benchmarks are re-recorded** with seared 0.4.0 and rusted 0.4.0. Against marshmallow, seared loads ~3.7× and
  dumps ~2.0× faster, and rusted runs ~11× faster on `load` and ~8× on `dump`. The dump ratio reads lower than
  0.3.4's ~9× because the pure-Python `dump` got faster, while rusted's held steady.

### Fixed

- **`inf` into an `Int` or an int-valued `Enum` raises `ValidationError`,** in both modes. It raised a bare
  `OverflowError`, which `except s.ValidationError` didn't catch.
- **The `format=` carrier hint reaches `Tuple` slots,** as it reaches a nested class since 0.3.1. Under
  `format='msgpack'` a `Bytes` slot stayed base64 while a top-level `Bytes` went native; it now carries raw bytes
  too, which changes what msgpack writes. Payloads written before still load, since `Bytes` reads either form.
- **`to_csv` names each column by its wire key,** the name `dump` writes and `from_csv` reads. It used attribute
  names, so a class with any `data_key` field failed with a bare `ValueError` from the `csv` module.

### Removed

- **Breaking:** `missing=`, the alias for `default=`, deprecated since 0.2.1. Passing it raises Python's own
  `TypeError` (an unexpected keyword argument); use `default=`, or `default_factory=` for a mutable default. The
  `Field.missing` attribute goes with it: a field's default is `f.default`, held as given, which is what
  construction, `load`, `seared.doc` and the accelerator spec now read.

## 0.3.4 — 2026-10-16

**Tagged releases, benchmark numbers generated from their results, and the pure-Python path back to full speed.** A
patch release that changes nothing `load` or `dump` returns or raises.

### Added

- **Releases are tagged.** A `Release Tag` workflow (`.github/workflows/release-tag.yml`) runs when a version merges
  to `master`. It checks that `pyproject.toml` and `seared/__init__.py` stamp the same version, then tags the merge
  `v<version>` and publishes a GitHub release. A merge that leaves the version unchanged finds it already released
  and stops there. 0.3.4 is the first tagged release; earlier ones stay untagged.
- **A test that the two version stamps agree**, so a mismatched bump fails before it reaches `master`.
- **A `no-commit-to-branch` hook** refuses a commit on `master`, which now moves only by merge. It is prek's
  built-in copy, so it fetches nothing.
- **`python -m bench --runs N`** times every case N times, interleaved across the cases so machine drift doesn't
  land on one, and tags each measurement with its run; the report records N. The docs' tables quote the median of
  the runs, and every ratio is a ratio of medians. An artifact recorded before runs were tagged still loads, as one
  run, and renders exactly as before.
- **Every benchmark number in the docs is generated, prose included.** The README's headline and accelerator ratios,
  and the benchmarks page's comparisons, run count and spread, are now inline blocks rendered from
  `bench/results.json`, like the tables beside them. A ratio reads to one decimal below 5× (`~3.3×`) and as a whole
  number from there up (`~11×`); a gap or spread is a whole percentage; a number the run can't supply reads `n/a`.
- **A run-to-run spread table** on the benchmarks page shows how far each column moved between runs, as
  `max / min - 1`, and the prose quotes the widest.
- **A `bench-tables` prek hook** fails a commit when a benchmark number in the README or the benchmarks page has
  drifted from `bench/results.json`.
- **A test that every scalar field survives its string form**, in strict mode: `deserialize(str(serialize(v)))`
  gives back `v` for every scalar kind the field registry exports, across its options and edge values, and the test
  fails if a new kind arrives without a case. zeared decodes topic captures and renders topic keys through these
  string forms. The test also records which kinds are safe as a single topic segment: `Path` and base64 `Bytes` can
  carry a `/`, and hex `Bytes` can't.
- **Tests of the benchmark table code**, on synthetic reports: medians, spread and ratios of medians over runs, a
  missing comparator dropping its column and reading `n/a` in prose, the prose rounding, the headline quoting strict
  mode, rendering that touches only the marked blocks, and `--check` writing nothing.

### Changed

- **README Setup installs a release by its tag:** `uv add … --tag v0.3.4`, or `pip install …@v0.3.4`. It says why:
  uv doesn't check a version specifier against a git source, so a source without a tag follows the tip of `master`.
- **README Development describes the hooks and the release process.** `feat/` and `fix/` branches merge into a
  `version/` branch, a `chore/version-bump-and-benches` branch bumps the version and re-records the benchmarks, and
  the version branch merges into `master`, where it is tagged.
- **The README headline quotes strict mode**, where it had quoted the lax column's ratio as if it were the
  default's: on the 2026-08-31 results, ~3.5× marshmallow on `load` had been lax, and strict was ~3.3×.
- **The benchmarks are re-recorded** on seared 0.3.4 and `rusted` 0.3.1, as the median of three runs. seared is
  ~3.6× marshmallow on `load` and ~1.9× on `dump`, and `rusted` is ~11× and ~9× over pure Python.
- **The benchmarks' provenance line names the number of runs**, and the reproduction steps record with `--runs 3`.

### Fixed

- **The pure-Python `load` and `dump` are back to 0.3.1's speed.** Two releases had slowed them without a test
  noticing; on the benchmark schema, `load` had lost about 16% and `dump` about 5%:
  - 0.3.2 moved the per-object default fill into a helper that imported `copy` and `Field` on every call, and `load`
    runs it once for every object it constructs, nested ones included;
  - 0.3.3's `FieldSpec` named tuples were unpacked in every `load` and `dump` loop, where CPython's fast path covers
    exact tuples only.

  The generated paths now iterate plain tuples (`__seared_fields__` still holds `FieldSpec`s), and the fill resolves
  `Field` once per class and runs inline in `__init__`. Nothing `load` or `dump` returns changes, and the `rusted`
  path was never affected. A new test fails if `load`, construction or `dump` runs an `import`.
- **Prose that had drifted from its own table:** on the 2026-08-31 results, strict versus lax on `dump` read ~14%
  where the table gave 13%, and the `rusted` dump gap ~15% where it gave 14%.
- **Spread figures the results never held** (~4%, ~9%, ±20%, and a 10.0× to 11.8× range for the `rusted` load ratio)
  are gone. The spread table replaces them.
- **The benchmarks page said to `uv pip install rusted`**, which isn't on a package index. It now says to install a
  wheel built from `rusted`, after any `uv sync`, which would otherwise remove it.

## 0.3.3 — 2026-10-15

**The lax `Bool` fix, and typed field specs.** A patch release, which changes nothing `load` or `dump` returns or
raises for a class the accelerator still takes. Changes that would are held for 0.4.0, which bumps `SPEC_ABI` once,
in step with a `rusted` release.

### Added

- **`s.FieldSpec`**, the type of each `__seared_fields__` entry: a `NamedTuple(attr, wire, field)`, typed on
  `Seared` as `ClassVar[tuple[FieldSpec, ...]]`. It is still a 3-tuple, so `for attr, wire, field in …` and tuple
  equality work as before. What changes is that `ty` now knows `field` is a `Field`, so probes like
  `getattr(f, 'many', False)` can go. `seared._core.decorator.FieldSpec`, a plain tuple alias until now, still
  imports, as the same class.
- **Benchmark tables are generated** from `bench/results.json` into the README and `docs/overview/benchmarks.md`,
  between `<!-- bench:NAME -->` markers. `python -m bench` re-renders them after a recorded run (a scratch `--out`
  run leaves the docs alone), and `python -m bench.tables --check` fails if they have drifted. The numbers are
  unchanged, from the same 2026-08-31 run.

### Changed

- **Breaking:** a `validate=False` class with a `Bool` field now loads `'false'`, `'0'`, `'no'` and `'off'` as
  `False`, not `True`. See Fixed.
- **Fewer classes accelerate:** a `validate=False` class with a `Bool` field, or one nesting such a class through
  `T`, is declined until `SPEC_ABI` 2. `rusted` 0.3.0 implements ABI 1, which still gives the old lax answer, and
  the ABI number is the only compatibility check seared makes; declining keeps the answer the same whichever wheel
  is installed. Strict `Bool` classes still accelerate. The reason reads
  `Cls.attr: Bool under validate=False is not accelerated until SPEC_ABI 2`. Lax mode is opt-in, so only a class
  declared `validate=False` loses acceleration.
- `docs/_core/accel.md` states the rule behind that decline: changing what an existing kind *means*, not only the
  shape of its spec, needs an ABI bump.
- **The docs state today's semantics plainly**, ahead of the 0.4.0 changes, in the README's *Limits* and a new *Load
  semantics* section of `docs/_core/decorator.md`:
  - `required` means the key is present, not that its value is non-null;
  - a wire `null` overrides a default;
  - construction doesn't check `required`;
  - unknown keys are ignored;
  - strict mode coerces numeric strings and truncates floats;
  - NaN dumps as a bare `NaN`, which `to_json(…, allow_nan=False)` refuses.
- **Docs that had drifted** now say what is so:
  - examples use `default=` and `default_factory=`, not `missing=`;
  - `field.md`'s options table lists `default`, `default_factory` and `doc`, and `decorator.md`'s lists `accel=`;
  - the README quick start's optional fields are `int | None` with `default=None`, as its own type-checking section
    asks;
  - the README's *Limits* heading no longer carries a version number, which had gone stale.

### Deprecated

- **`missing=` is removed in 0.4.0**, and the docs now say so. In 0.3.3 it still works, as an alias for `default=`.

### Fixed

- **Lax `Bool` no longer reads `'false'` as `True`.** Under `@s.seared(validate=False)`, `Bool` returned
  `bool(value)` before it reached its spelling table, so `'false'`, `'0'`, `'no'` and `'off'` all loaded as `True`.
  Lax mode now reads the strict spellings first, after `strip().lower()`: `true`, `1`, `yes` and `on` are `True`;
  `false`, `0`, `no` and `off` are `False`. Anything else still falls back to truthiness (`'maybe'` is `True`, `''`
  is `False`), so lax mode still never raises. Bools and ints load as before, and strict mode was always right.
  `docs/fields/bool_.md` gains a strict-versus-lax table.
- **`missing=`'s deprecation warning points at the caller.** It pointed at the dataclass-generated `__init__`
  (`<string>`), and for `T`, `Tuple` and `Enum`, whose constructors add frames of their own, into seared itself.
  Default warning filters hid it, and anyone who saw it was sent to the wrong file. It now skips the field's own
  constructor frames and lands on the line that built the field.

## 0.3.2 — 2026-10-03

**`__post_init__` sees its defaults** on construction, as it already did on `load`.

### Changed

- `seared.doc.introspect` dedupes the classes a schema references by identity, keeping first-seen order. Its output
  is the same.
- **Dependencies:** the lockfile is refreshed (numpy, pandas, polars, ruff, ty, prek and pygments among others). No
  dependency ranges changed.

### Fixed

- **`__post_init__` sees resolved defaults.** The dataclass `__init__` calls the hook before seared fills in omitted
  fields, so a hook reading one got the raw `Field` object, which is truthy. `load` resolves every default before
  constructing, so the two paths disagreed. seared now wraps `__post_init__` to fill in defaults first and then call
  the original, passing any `InitVar` arguments through. A subclass re-wraps an inherited hook with its own fields,
  so the hook sees the subclass's omitted fields filled in too; filling twice is harmless. `docs/_core/decorator.md`
  and `docs/overview/architecture.md` describe the wrapping.

## 0.3.1 — 2026-09-04

**Two fixes from integrating the accelerator**: one in the Python path, one in the accelerator's gate.

### Changed

- **Fewer classes accelerate:** a class with a plain dataclass attribute that isn't a seared `Field` (`b: int = 5`)
  is declined. That attribute never reaches the accelerator's spec, and a compiled backend builds instances with
  `__new__` and slot assignment, so its slot was left unset and `repr` or `==` raised. The Python path runs
  `__init__` and was fine. The reason reads like `Cls.b is a plain dataclass field, not a seared Field`. Classes
  with their own `__init__` or `__post_init__` are declined as before.
- The accelerator docs and the README give the new rule. Their `accel_status()` example now shows `rusted` 0.2.1,
  supporting seared `>=0.3.1,<0.4`.

### Fixed

- **The `format=` carrier hint crosses nesting.** `T` and `Union` called the nested class without it, so under
  `format='msgpack'` a `Bytes` or `NDArray` inside a nested class fell back to base64 while its top-level siblings
  went native. Both now pass it on. `docs/fields/t.md` says so.

## 0.3.0 — 2026-08-31

**The accelerator, shipped.** Docs, benchmarks and typing on top of 0.2.8's seam, now that `rusted` 0.2.0 implements
it.

### Added

- **`__seared_accel__` is declared on `Seared`**, as `ClassVar[AccelInfo]`, so reading it type-checks. An
  undecorated subclass reads `AccelInfo(accelerated=False, reason='class is not decorated with @seared')` instead of
  raising `AttributeError`. `__seared_fields__` gains a doc comment beside it.
- **A `seared+rusted` benchmark.** With `rusted` 0.2.0, load is about 11× and dump about 9× faster than pure seared,
  about twice pydantic's speed on the bench schema; pure seared stays 4–5× behind pydantic. The plain seared rows
  are pinned to `accel=False`, so an installed accelerator can't turn them into compiled numbers. Runs vary by a few
  percent, more when accelerated, and the docs say to read the ratios as approximate.

### Changed

- **Installing the accelerator:** `docs/_core/accel.md` no longer promises a `seared[core]` extra. `rusted` is
  installed beside seared (`uv add git+https://www.github.com/bwiswell/rusted.git`), and neither declares a
  dependency on the other, so a missing or broken wheel can't break seared. `deptry` is configured to match.
- **Tier 2 is supported**, as `rusted` has implemented it since 0.1.1: `UUID`, the date and time types, `Decimal`,
  `Bytes`, `Enum`, `Path` and `Dict`. These don't reach Tier 1's speed, since their time goes on building Python
  objects either way; the gain is that one `Bytes` field no longer keeps a whole class on the Python path. The docs
  say why Tier 3 waits: `Union` consumes several of its parent's keys, `Tuple` has a field per slot, and the frame
  fields sit behind optional imports.
- **The compatibility ceiling is raised:** the reference backend and the documented status move from `>=0.2.8,<0.3`
  to `>=0.2.8,<0.4`.
- **The README is rewritten for 0.3.x**, and the benchmarks re-recorded.

## 0.2.9 — 2026-08-31

**Typing fixes**, and a runtime fault they turned up.

### Changed

- **`Seared.dump` and `load` declare `format=`** on the base, as the decorator's implementations take it, so
  zeared's `Cls.dump(obj, format='msgpack')` type-checks. A test keeps the declarations and the implementations
  identical.
- **`T` takes only a seared class**, as `Union` has since 0.2.5: `T(schema)` is typed `type[Seared]`, so `ty` flags
  `T(NotASearedClass)`, which constructs and then fails on `.dump`. The doc generator skips such a reference instead
  of crashing.
- `Path(concrete=...)` is typed `type[PurePath]`; `VariantDoc.cls` and `FieldDoc.nested` are typed `type[Seared]`.

### Fixed

- **`load(data=...)` and `dump(obj=...)` work.** The implementations the decorator attaches named their parameters
  `d` and `o`, so a call through the documented names type-checked and then raised `TypeError`.

## 0.2.8 — 2026-08-31

**The accelerator seam.** seared's Python path stays canonical; when an optional backend is installed, `@seared`
swaps its generated `load` and `dump` for compiled ones. The backend is
[`rusted`](https://github.com/bwiswell/rusted), a separate Rust/PyO3 project. See `docs/_core/accel.md`.

### Added

- **Spec emission:** seared walks a class's fields and hands the backend a plain-data spec, so the backend never
  sees a `Field`. The spec is versioned by `SPEC_ABI`, and a backend declaring another number isn't used.
- **The rules:**
  - seared alone knows seared;
  - acceleration is gated on a field's exact class, since a subclass of `s.Int` may override `deserialize`;
  - it is all or nothing per class, recursively through `T`;
  - a backend can only ever be a no-op: a missing module, an ABI mismatch or a backend that raises each records a
    reason and falls back to Python.
- **Field coverage:** Tier 1 (`Int`, `Float`, `Str`, `Bool`, `T`) is supported; Tier 2 (`UUID`, the date and time
  types, `Decimal`, `Bytes`, `Enum`, `Path`, `Dict`) is planned; Tier 3 (`Tuple`, `Union`, `NDArray`, the frames)
  waits. Classes with their own `__init__` or `__post_init__` are declined.
- **Controls:** `@s.seared(accel=False)`, and the environment variables `SEARED_ACCEL=auto|off|require` and
  `SEARED_ACCEL_BACKEND=<module>`. `require` lets CI assert that the backend loaded.
- **Introspection:** `Cls.__seared_accel__`, with `s.accel_status()` and `s.AccelInfo` at the package root.
- **A reference backend** for differential tests: `tests/refcore.py` implements the backend protocol in pure Python,
  and the whole suite runs against it with `SEARED_ACCEL=require SEARED_ACCEL_BACKEND=refcore`, giving the same
  values and the same error messages.
- `docs/overview/architecture.md` gains the decorator's sixth step: offer the class to a backend.

## 0.2.7 — 2026-08-30

**`deptry`.** Tooling only.

### Added

- **`deptry`** in the dev dependencies and as a `prek` hook, after `ruff` and before `ty`. The bench's comparators
  (`marshmallow`, `pydantic`) are mapped to their modules, so `bench/` stays in the check.

## 0.2.6 — 2026-08-30

**`ruff`**, linting and formatting, as `prek` hooks. The largest churn of the 0.2.x line, all of it mechanical.

### Added

- **`ruff`** in the dev dependencies and as `prek` hooks for checking and formatting: `select = ["ALL"]`, line
  length 120, target `py314`, google docstrings, single quotes. Each seared-specific ignore gives its reason:
  `ANN401` because `Any` is the wire boundary type, `FBT001` and `FBT002` because `validate: bool = True` is public
  API, `A002` because the public keyword is spelled `format=`. Markdown is left unformatted, since the docs align
  declarations by hand and show JSON in Python blocks.

### Changed

- Source, tests and the type-check fixtures are reformatted, and `__all__` is sorted. Behaviour is unchanged.

## 0.2.5 — 2026-08-30

**`prek`, and a `ty` gate.**

### Added

- **`prek` hooks:** `.pre-commit-config.yaml` runs `uv run ty check` on commits that touch Python. Install it once
  per clone with `uv run prek install`. `prek` joins the dev dependencies.
- **The eight codec methods are declared on `Seared`** (`to_` and `from_` for JSON, TOML, YAML and CSV), so calls to
  them type-check. The decorator still attaches them, as it does `dump` and `load`.

### Changed

- **`Union` takes only seared classes:** its `variants` and `default` are typed `type[Seared]`, as is `seared.doc`'s
  API (`introspect`, `document`, `collect`), and `is_seared_class` is a `TypeGuard`.
- `Union.deserialize`'s first parameter is named `value`, as on every other field.
- `ty` skips `tests` and the bench suites whose comparators a default dev sync doesn't install.

## 0.2.4 — 2026-08-30

**The benchmarks reworked**, and the headline numbers corrected.

### Added

- **`python -m bench`:** the bench is a package, with a shared harness, a suite per library and a
  `bench/results.json` written by each recorded run. It ships in the repo but not in the sdist.
- **pydantic v2 as a comparator**, and a `bench` extra (`marshmallow`, `pydantic`) for the bench alone, never a
  runtime dependency.

### Changed

- **The README's claims are revised down.** 0.2.0's "~8× faster load, 2.6–3.1× faster dump than marshmallow" was
  measured against marshmallow 3.26. Against marshmallow 4.3.1, seared loads about 3.7× and dumps about 1.8× as
  fast: marshmallow 4 closed part of the gap, and seared didn't regress. pydantic 2.13.5 is 4–5× faster than seared.
  The README now says "Fast for pure Python", and that seared's trade is having no runtime dependencies.
- `docs/overview/benchmarks.md` is rewritten around method, results and caveats.

## 0.2.3 — 2026-08-29

**Python 3.14.**

### Changed

- **Breaking:** the Python floor rises from 3.11 to 3.14 (`requires-python = ">=3.14,<4.0"`). No source changes.
- **Dependencies:** the lockfile drops the wheels only older Pythons needed.

## 0.2.2 — 2026-08-28

**Schema docs, generated** from `@seared` classes, as Markdown.

### Added

- **`seared.doc`:**
  - `introspect(cls)` returns a render-agnostic `SchemaDoc`, with `FieldDoc`, `EnumDoc` and `VariantDoc`;
  - `document(cls)` renders one class's page;
  - `collect(target)` finds the seared classes in a module or package, following `T` references;
  - `build_docs(target)` returns `{path: markdown}` for all of them.
- **The `seared-doc` command**, or `python -m seared.doc <module-or-package> [-o docs] [--check]`. `--check` fails
  when the docs are stale, for CI.
- **`doc=` on every field:** a description for people (units, meaning, provenance), never serialized, which the
  generated pages show.
- `document` and `introspect` at the package root.

## 0.2.1 — 2026-08-25

**Type-checker support.** `@s.seared` declarations type-check cleanly under `ty`, pyright and mypy.

### Added

- **PEP 681 `@dataclass_transform`** on `@seared` (`kw_only_default=True`, with every field constructor as a field
  specifier), so `x: str = s.Str(...)` reads as a dataclass field.
- `.pyi` stubs for every field constructor, returning `Any` so the annotation sets the attribute's type, and a
  `py.typed` marker. Downstream projects can drop their `ty` excludes for `@seared` modules.
- **`default=` and `default_factory=`** on fields: the names type checkers use to tell required from optional. A
  field with neither is a required argument to the checker, even where seared would let it be omitted.
- **`tests/typecheck/`** keeps the support honest: the canonical idiom must give no `ty` diagnostics, and a missing
  argument, an unknown argument and an unknown attribute must each be flagged.

### Changed

- `Seared.load` and `loads` return `Self`, so they're typed as the concrete class.
- `default_factory` builds a fresh value per instance and is the way to give a mutable default. A mutable
  `default=[...]` is still deep-copied per instance.
- **Dependencies:** `ty` joins the dev dependencies.

### Deprecated

- **`missing=`**, for `default=` and `default_factory=`. It still works, as an alias for `default=`, but warns with
  a `DeprecationWarning`, and type checkers can't see it. The README's examples are migrated: `s.Int(missing=5)`
  becomes `s.Int(default=5)`, and `missing=[]` becomes `default_factory=list`.

## 0.2.0 — 2026-04-26

**A rewrite.** seared stops wrapping marshmallow and becomes a self-contained serialization library with no runtime
dependencies.

### Added

- **The `@s.seared` pipeline:** it wraps `dataclasses.dataclass`, builds the field spec once at decoration, and
  generates `load` and `dump` classmethods that walk it. `Cls.__seared_fields__` exposes the spec as
  `(attr, wire_key, Field)` triples.
- **Strict validation by default:** `validate=True` raises `ValidationError` on a type or shape mismatch, on `load`
  and on `dump`. `@s.seared(validate=False)` is a lax mode that skips type guards and coerces where the intent is
  obvious.
- **Errors:** `SearedError`, a `ValueError`, and its subclass `ValidationError`, both at the package root.
- `dump=False` on a field leaves it out of the output, for computed values.
- Mutable `missing` defaults (`list`, `dict`, `set`, `frozenset`) are deep-copied per instance.
- **Field types**, with a module and a doc page each:
  - scalars: `Bool`, `Int`, `Float`, `Str`, `Bytes`;
  - dates and times: `Date`, `DateTime`, `Time`, `TimeDelta`;
  - `Decimal` (a lossless string on the wire; `as_number=True` gives a JSON number), `UUID`, and `Path` (always a
    POSIX string, so round trips match across platforms);
  - containers and composition: `Dict`, `Tuple`, `Enum`, and `T` for a nested seared class;
  - **`Union`**, a tagged union over `{tag, payload}` envelopes that loads typed variant instances. Envelopes may be
    flat or nested (`payload_key`). A class may hold several Unions if their wire keys don't overlap, which is
    checked when the class is defined. `Union(default=Variant)` takes an unknown tag to a fallback variant instead
    of raising, for schema evolution;
  - behind extras: `NDArray` (`seared[numpy]`), `PandasFrame` (`seared[pandas]`), `PolarsFrame` (`seared[polars]`).
- **Codecs:** every class gets `to_*` and `from_*` classmethods for JSON, TOML, YAML and CSV. JSON, TOML reading and
  CSV use the standard library; YAML and TOML writing need the `seared[yaml]` and `seared[toml]` extras. `from_*`
  takes a path or the content itself, and `from_csv` returns `list[Cls]`.
- **The `format=` carrier hint:** `Cls.dump(obj, format='msgpack')` tells each field the carrier, so `Bytes` and
  `NDArray` go as native binary instead of base64, which is a third larger. Only `dump` and `load` take it; there is
  no msgpack codec.
- **Extras:** `numpy`, `yaml`, `toml`, `pandas`, `polars` and `all`.
- **Docs:** a `docs/` tree (core internals, a page per field and per format, the architecture, benchmarks) and a
  much larger README.
- **Benchmarks** against marshmallow 3.26: about 8× on load and 2.6–3.1× on dump, mostly from lower per-call
  overhead (`__slots__`, a prebuilt spec, no schema layer) rather than skipped validation. Strict and lax modes
  differ by 1% on load and 16% on dump. Re-measured in 0.2.4.

### Changed

- **Breaking:** `@s.seared` builds `__slots__` dataclasses, where it applied a plain `dataclass` before.
  `@s.seared(slots=False)` opts out.
- **Breaking:** a field's default is the `missing=` keyword, not its first positional argument: `s.Int(5)` becomes
  `s.Int(missing=5)`. `required=True`, `data_key=`, `many=` and `keyed=` carry over.
- **Breaking:** a nested class is referenced directly, `s.T(MyClassA, …)`, not as `s.T(MyClassA.SCHEMA, …)`.
- **Breaking:** the flat modules (`seared/int.py`, `bool.py`, `_enum.py`, …) become `seared/fields/*_.py`. Every
  public name is still exported from the package root.
- **Dependencies:** none at runtime. `numpy` moves to the `seared[numpy]` extra, and `NDArray` raises a helpful
  `ImportError` without it. Python stays at 3.11 and up.
- The tests split from one file into a module per source file, and pytest runs in importlib mode.

### Removed

- **Breaking:** marshmallow, and the `Schema` internals with it: `BaseSchema`, the `post_load` and `post_dump`
  hooks, and `Cls.SCHEMA`.

## 0.1.0 — 2026-04-18

**A marshmallow wrapper**, and the first working release: a dataclass becomes a schema-backed serializer.

### Added

- **`@s.seared` and `s.Seared`.** The decorator applies `dataclass` and generates a marshmallow `Schema` from the
  class's `Field` defaults. A `post_dump` hook strips skipped values, and attributes are always read with `getattr`,
  so a class's own `__getitem__` can't shadow them during serialization.
- **`load`, `dump`, `loads` and `dumps`**, the last two taking and giving JSON strings. A nested class is referenced
  through its `Cls.SCHEMA`.
- **Field types**, a flat module each: `Bool`, `Int`, `Float`, `Str`, `Date`, `DateTime`, `Time`, `Dict`, `Enum`,
  `NDArray`, and `T` for nesting. The base `Field` handles `data_key`, `many` (lists) and `keyed` (string-keyed
  dicts), and a field's default is its first positional argument.
- **Packaging:** built with `hatchling`, for Python 3.11 and up, depending on `marshmallow` (3.26.1 and up, below 4)
  and `numpy` (2.4.2 and up, below 3). It installs from git; the README covers pip, poetry and uv.
