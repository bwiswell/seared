# `doc/generate.py` — doc sets and the CLI

Runs [`introspect`](introspect.md) and [`render`](render.md) over a whole
module or package: discovery, paths, cross-links, the index, and the
drift check. The per-class renderer is a parameter, so zeared reuses all
of it with its own.

## `collect(target) -> list[type[Seared]]`

Imports `target` and, for a package, every submodule under it. A
submodule that fails to import is skipped with a warning on stderr. It
returns every `@seared` class found in them, sorted by module then name.

- **A class whose name starts with `_` is left out**, since a private base's
  fields already appear on its concrete subclasses.
- **Every class a found one refers to is added**, transitively, private or
  not and wherever it lives, so no link dangles.

## `build_docs(target, *, render_one=None) -> dict[str, str]`

The whole doc set, in memory: `{relative POSIX path: Markdown}`, with
`index.md` included. No disk I/O.

- **Paths mirror the package tree.** `mypkg.models.telemetry.Reading`,
  built for `mypkg.models`, lands at `telemetry/Reading.md`. A class from
  outside the target, pulled in by reference, lands at the root. Two
  classes on one path print a warning.
- **Links are relative**, from each page to the page of the class it
  refers to.
- **`index.md`** groups the models by their first directory (`(root)` for
  the top level), one table of name and summary per group.
- **`render_one(cls, link_for) -> str`** renders one page. The default is
  seared's own (`render_schema` over `introspect`).

## The CLI

```
seared-doc TARGET [-o DIR] [--check]
python -m seared.doc TARGET [-o DIR] [--check]
```

| Option | |
|---|---|
| `TARGET` | the module or package to document, as a dotted path |
| `-o`, `--output` | the directory to write to, or check against (default `docs`) |
| `--check` | compare instead of writing |

A `TARGET` that doesn't import raises its `ImportError`; only submodules
under it are skipped with a warning.

- **Writing** creates or overwrites each page whose content changed, and
  prints `N written, M unchanged → DIR/`. It never deletes: a page for a
  class that's gone stays until you remove it.
- **`--check`** writes nothing. It exits 0 with `N doc(s) up to date.`,
  or 1 after listing each page as `missing:` or `stale:` on stderr. A page
  for a class that no longer exists isn't reported.

`main(argv=None, *, render_one=None, prog=None)` is the entry point both
spellings call, and returns the exit code. `render_one` and `prog` are how
another package (zeared's `python -m zeared.doc`) runs the same CLI with
its own renderer and name.
