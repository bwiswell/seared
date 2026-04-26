# `formats/__init__.py` — codec orchestrator

Every `@s.seared` class gets per-format `to_*` / `from_*` classmethods
auto-attached at decorator time via `_attach_format_methods`. Stdlib
formats (JSON, TOML-read, CSV) work out of the box; the rest are
behind optional extras.

## Methods attached to every seared class

| Method | Returns / accepts | Extra |
|--------|-------------------|-------|
| `Cls.to_json(obj, indent=None, **kwargs)` | string content | — (stdlib) |
| `Cls.from_json(source)` | `Cls` instance | — (stdlib) |
| `Cls.to_toml(obj)` | string content | `seared[toml]` |
| `Cls.from_toml(source)` | `Cls` instance | — (stdlib `tomllib`) |
| `Cls.to_yaml(obj)` | string content | `seared[yaml]` |
| `Cls.from_yaml(source)` | `Cls` instance | `seared[yaml]` |
| `Cls.to_csv(items)` | string content | — (stdlib) |
| `Cls.from_csv(source)` | `list[Cls]` | — (stdlib) |

## `_attach_format_methods(cls)`

Called once per `@s.seared` class at decorator time
(`_core/decorator.py::_build`). Each method is a thin shim over the
format module — keeps the bound classmethod signatures clean while
letting the codec modules do the real work.

The codec modules are imported eagerly when `seared.formats` first
loads, but their optional dependencies are not — `to_yaml` raises a
helpful `ImportError` only when called without `seared[yaml]` installed.

## Per-format docs

- [`csv_.md`](csv_.md) — class-method-only flat-record codec.
- [`json_.md`](json_.md) — stdlib-only JSON codec.
- [`toml_.md`](toml_.md) — read free, write via `seared[toml]`.
- [`yaml_.md`](yaml_.md) — both directions via `seared[yaml]`.
- [`_common.md`](_common.md) — `read_source` path-vs-content detection
  helper used by every `from_*` method.
