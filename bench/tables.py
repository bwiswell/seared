"""Render the benchmark tables in the docs from ``bench/results.json``.

The README and ``docs/overview/benchmarks.md`` carry the numbers between
``<!-- bench:NAME -->`` / ``<!-- /bench:NAME -->`` markers: everything inside
a pair is generated, everything outside it is prose. ``python -m bench``
re-renders them after recording a run; ``python -m bench.tables`` does it
from the committed artifact alone, and ``--check`` exits non-zero when a doc
has drifted from it. Hand-copied numbers were the likeliest way for a doc to
disagree with its own artifact.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .harness import Measurement, Report

_ROOT = Path(__file__).parent.parent
RESULTS = Path(__file__).parent / 'results.json'
DOCS = (_ROOT / 'README.md', _ROOT / 'docs' / 'overview' / 'benchmarks.md')

#: ``(library, variant, header)`` in display order. A column the run has no
#: measurement for (a comparator that wasn't installed) is left out.
_COLUMNS = (
    ('marshmallow', 'default', '`marshmallow`'),
    ('seared', 'strict', '`seared` (strict)'),
    ('seared', 'lax', '`seared` (lax)'),
    ('pydantic', 'default', '`pydantic`'),
    ('seared+rusted', 'strict', '`seared+rusted`'),
)

#: The pure-Python peer the ``seared`` columns are quoted against.
_BASELINE = ('marshmallow', 'default')

#: Spelled by name: ruff (RUF001) reads the literal sign as a typo for ``x``.
_TIMES = '\N{MULTIPLICATION SIGN}'

_BLOCK = re.compile(r'(<!-- bench:(?P<name>[\w-]+) -->)(?P<body>.*?)(<!-- /bench:(?P=name) -->)', re.DOTALL)


def _table(rows: list[list[str]]) -> str:
    """A padded Markdown table; the first row is the header."""
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]

    def line(cells: list[str]) -> str:
        return '| ' + ' | '.join(c.ljust(w) for c, w in zip(cells, widths, strict=True)) + ' |'

    rule = '|' + '|'.join('-' * (w + 2) for w in widths) + '|'
    return '\n'.join([line(rows[0]), rule, *(line(r) for r in rows[1:])])


def _by_key(report: Report) -> dict[tuple[str, str, str], Measurement]:
    return {(m.library, m.variant, m.op): m for m in report.measurements}


def _columns(report: Report) -> list[tuple[str, str, str]]:
    have = {(m.library, m.variant) for m in report.measurements}
    return [c for c in _COLUMNS if (c[0], c[1]) in have]


def ops_table(report: Report) -> str:
    """``ops/s`` per (op, column), with the ``seared`` columns' ratio to the baseline."""
    found = _by_key(report)
    columns = _columns(report)
    rows = [['Op', *(header for _, _, header in columns)]]
    for op in ('load', 'dump'):
        row = [op]
        for library, variant, _ in columns:
            m = found[library, variant, op]
            cell = f'{m.ops_per_s:,.0f} ops/s'
            base = found.get((*_BASELINE, op))
            if library == 'seared' and base is not None:
                cell += f' (~{m.ops_per_s / base.ops_per_s:.1f}{_TIMES})'
            row.append(cell)
        rows.append(row)
    return _table(rows)


def us_table(report: Report) -> str:
    """Microseconds per call, same layout as :func:`ops_table`."""
    found = _by_key(report)
    columns = _columns(report)
    rows = [['Op', *(header for _, _, header in columns)]]
    rows.extend(
        [op, *(f'{found[lib, var, op].us_per_op:.1f} µs' for lib, var, _ in columns)] for op in ('load', 'dump')
    )
    return _table(rows)


def run_line(report: Report) -> str:
    """When, on what, and against which versions — the provenance of the tables."""
    versions: dict[str, str] = {}
    for m in report.measurements:
        if m.library == 'seared+rusted':
            # Recorded as ``<seared>/rusted <rusted>``; seared's own rows carry the first half.
            versions.setdefault('rusted', m.version.partition('/rusted ')[2])
        else:
            versions.setdefault(m.library, m.version)
    order = ('seared', 'rusted', 'marshmallow', 'pydantic')
    named = ', '.join(f'{lib} {versions[lib]}' for lib in order if lib in versions)
    return f'{report.timestamp[:10]}, Python {report.python}, {report.iterations:,} iterations; {named}'


def blocks(report: Report) -> dict[str, str]:
    """Every generated block by marker name. Tables sit on lines of their own."""
    return {
        'ops': f'\n{ops_table(report)}\n',
        'us': f'\n{us_table(report)}\n',
        'run': run_line(report),
    }


def render(text: str, generated: dict[str, str]) -> str:
    """``text`` with every marker pair's body replaced by its generated block.

    Raises:
        KeyError: a marker names a block this module doesn't generate.
    """

    def replace(match: re.Match[str]) -> str:
        return f'{match[1]}{generated[match["name"]]}{match[4]}'

    return _BLOCK.sub(replace, text)


def update(report: Report, *, check: bool = False) -> list[Path]:
    """Re-render :data:`DOCS` from ``report``; return the files that differed.

    With ``check=True`` nothing is written: the return value is the drift.
    """
    generated = blocks(report)
    drifted = []
    for path in DOCS:
        text = path.read_text(encoding='utf-8')
        new = render(text, generated)
        if new != text:
            drifted.append(path)
            if not check:
                path.write_text(new, encoding='utf-8')
    return drifted


def main() -> None:
    """Re-render the docs' tables from the committed results, or check them."""
    parser = argparse.ArgumentParser(prog='python -m bench.tables', description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='exit 1 if a doc has drifted from results.json')
    args = parser.parse_args()

    drifted = update(Report.from_json(RESULTS), check=args.check)
    for path in drifted:
        print(f'{"drifted" if args.check else "updated"}: {path.relative_to(_ROOT)}')
    if args.check and drifted:
        sys.exit(1)


if __name__ == '__main__':
    main()
