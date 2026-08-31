"""Doc-set generation.

Discover models, mirror the package tree, cross-link, build the index,
and diff for ``--check``.

Factored apart from any single renderer so zeared reuses the whole pipeline
(discovery / pathing / links / index / check) with its own Message-aware
``render_one``.
"""

from __future__ import annotations

import argparse
import importlib
import os
import pkgutil
import sys
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from seared._core.base import Seared

from .introspect import introspect, is_seared_class
from .render import LinkFor, render_schema

# render_one(cls, link_for) -> markdown page for one class.
RenderOne = Callable[[type[Seared], LinkFor], str]


def _import_tree(target: str) -> list[object]:
    """Import ``target`` and, if it's a package, all its submodules."""
    root = importlib.import_module(target)
    modules = [root]
    path = getattr(root, '__path__', None)
    if path is not None:
        for info in pkgutil.walk_packages(path, prefix=target + '.'):
            try:
                modules.append(importlib.import_module(info.name))
            except Exception as exc:  # noqa: BLE001 — skip unimportable submodules
                print(f'warning: skipped {info.name}: {exc}', file=sys.stderr)
    return modules


def collect(target: str) -> list[type[Seared]]:
    """All ``@seared`` classes reachable from ``target``.

    Includes the transitive closure of referenced (nested / variant)
    classes, deduped and sorted.
    """
    found: dict[int, type[Seared]] = {}

    def add(cls: type[Seared]) -> None:
        if id(cls) in found:
            return
        found[id(cls)] = cls
        for ref in introspect(cls).references:
            # ``references`` is typed ``type[Seared]``, but annotations are not
            # enforcement: ``T(NotASearedClass)`` still *constructs* at runtime
            # (it only fails later, on ``.dump``). The guard keeps a mistyped
            # schema out of the doc set instead of crashing the generator.
            if is_seared_class(ref):
                add(ref)

    for module in _import_tree(target):
        for obj in vars(module).values():
            # Skip private/abstract bases (``_TagAlert``) from the top-level set —
            # their fields already appear inline on concrete subclasses. Closure
            # (``add``) still pulls in a ``_``-prefixed class if a public model
            # *references* it (T / Union target), so links never dangle.
            if is_seared_class(obj) and not obj.__name__.startswith('_'):
                add(obj)
    return sorted(found.values(), key=lambda c: (c.__module__, c.__name__))


def _rel_path(cls: type, target: str) -> PurePosixPath:
    """Output path for a class, mirroring its module tree under the target.

    A class outside the target package (pulled in by reference) lands at the
    doc-set root.
    """
    module = cls.__module__
    if module == target or module.startswith(target + '.'):
        suffix = module[len(target) :].lstrip('.')
        dirs = suffix.split('.')[:-1] if suffix else []
    else:
        dirs = []
    return PurePosixPath(*dirs, f'{cls.__name__}.md')


def _index(pages: dict[PurePosixPath, tuple[type[Seared], str]]) -> str:
    """Build ``index.md`` grouping models by top-level category dir."""
    groups: dict[str, list[tuple[str, PurePosixPath, str | None]]] = {}
    for path, (cls, _content) in pages.items():
        category = path.parts[0] if len(path.parts) > 1 else '(root)'
        summary = introspect(cls).summary
        groups.setdefault(category, []).append((cls.__name__, path, summary))
    out = ['# Schema index', '']
    for category in sorted(groups):
        out += [f'## {category}', '', '| model | summary |', '|-------|---------|']
        for name, path, summary in sorted(groups[category]):
            out.append(f'| [{name}]({path.as_posix()}) | {(summary or "").replace("|", chr(92) + "|")} |')
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


def build_docs(target: str, *, render_one: RenderOne | None = None) -> dict[str, str]:
    """Return ``{relative_posix_path: markdown}`` for the whole doc set.

    Includes ``index.md``. Pure — no disk I/O.
    """
    if render_one is None:
        render_one = lambda cls, link_for: render_schema(introspect(cls), link_for=link_for)  # noqa: E731
    classes = collect(target)
    path_of: dict[type, PurePosixPath] = {}
    for cls in classes:
        p = _rel_path(cls, target)
        if p in path_of.values():
            print(f'warning: output path collision at {p} ({cls.__name__})', file=sys.stderr)
        path_of[cls] = p

    pages: dict[PurePosixPath, tuple[type[Seared], str]] = {}
    for cls in classes:
        here = path_of[cls]

        def link_for(ref: type, _here: PurePosixPath = here) -> str:
            target_path = path_of.get(ref)
            if target_path is None:
                return f'{ref.__name__}.md'
            rel = os.path.relpath(target_path.as_posix(), _here.parent.as_posix())
            return PurePosixPath(rel).as_posix()

        pages[here] = (cls, render_one(cls, link_for))

    out = {path.as_posix(): content for path, (_c, content) in pages.items()}
    out['index.md'] = _index(pages)
    return out


def write_docs(docs: dict[str, str], outdir: str) -> tuple[int, int]:
    """Write pages under ``outdir`` (create/overwrite ``.md`` only).

    Returns ``(written, unchanged)``.
    """
    written = unchanged = 0
    for rel, content in sorted(docs.items()):
        path = Path(outdir) / rel
        if path.exists() and path.read_text(encoding='utf-8') == content:
            unchanged += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        written += 1
    return written, unchanged


def check_docs(docs: dict[str, str], outdir: str) -> list[str]:
    """Return a list of drift descriptions (empty == in sync)."""
    drift = []
    for rel, content in sorted(docs.items()):
        path = Path(outdir) / rel
        if not path.exists():
            drift.append(f'missing: {rel}')
            continue
        if path.read_text(encoding='utf-8') != content:
            drift.append(f'stale:   {rel}')
    return drift


def main(argv: list[str] | None = None, *, render_one: RenderOne | None = None, prog: str | None = None) -> int:
    """CLI entry point for ``seared-doc``. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description='Generate Markdown schema docs from @seared / @zeared classes.',
    )
    parser.add_argument('target', help='module or package to scan (dotted path)')
    parser.add_argument('-o', '--output', default='docs', help='output directory (default: ./docs)')
    parser.add_argument('--check', action='store_true', help='verify docs are up to date; exit 1 on drift (no writes)')
    args = parser.parse_args(argv)

    docs = build_docs(args.target, render_one=render_one)

    if args.check:
        drift = check_docs(docs, args.output)
        if drift:
            print(f'{len(drift)} doc(s) out of date under {args.output!r}:', file=sys.stderr)
            for line in drift:
                print(f'  {line}', file=sys.stderr)
            print('run without --check to regenerate.', file=sys.stderr)
            return 1
        print(f'{len(docs)} doc(s) up to date.')
        return 0

    written, unchanged = write_docs(docs, args.output)
    print(f'{written} written, {unchanged} unchanged → {args.output}/')
    return 0
