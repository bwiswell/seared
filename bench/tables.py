"""Render the benchmark tables in the docs from ``bench/results.json``.

The README and ``docs/overview/benchmarks.md`` carry the numbers between
``<!-- bench:NAME -->`` / ``<!-- /bench:NAME -->`` markers: everything inside
a pair is generated, everything outside it is prose. ``python -m bench``
re-renders them after recording a run; ``python -m bench.tables`` does it
from the committed artifact alone, and ``--check`` exits non-zero when a doc
has drifted from it. Hand-copied numbers were the likeliest way for a doc to
disagree with its own artifact.

Every number is a median over the report's runs (``python -m bench --runs N``),
and every ratio is a ratio of medians. A one-run report renders exactly as it
did before runs were recorded: the median of one value is that value.
"""

from __future__ import annotations

import argparse
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from .harness import Report

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from .harness import Measurement

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

#: The ops every case times, in display order.
_OPS = ('load', 'dump')

#: Spelled by name: ruff (RUF001) reads the literal sign as a typo for ``x``.
_TIMES = '\N{MULTIPLICATION SIGN}'

#: What a number the report can't supply renders as.
_NA = 'n/a'

#: Runs a spread needs: one run has nothing to move against.
_SPREAD_MIN_RUNS = 2

_BLOCK = re.compile(r'(<!-- bench:(?P<name>[\w-]+) -->)(?P<body>.*?)(<!-- /bench:(?P=name) -->)', re.DOTALL)

#: One case, and so one column: ``(library, variant)``.
type Case = tuple[str, str]


class Results:
    """A report's measurements as medians and spread over its runs."""

    def __init__(self, report: Report) -> None:
        """Group ``report``'s measurements by ``(library, variant, op)``, one per run."""
        grouped: dict[tuple[str, str, str], list[Measurement]] = defaultdict(list)
        for m in report.measurements:
            grouped[m.library, m.variant, m.op].append(m)
        self.report = report
        self._grouped = dict(grouped)

    def has(self, case: Case) -> bool:
        """Whether ``case`` was measured at all."""
        return any((*case, op) in self._grouped for op in _OPS)

    def median(self, case: Case, op: str, metric: str = 'ops_per_s') -> float | None:
        """The median of ``metric`` over ``case``'s ``op`` runs, or ``None`` if unmeasured."""
        runs = self._grouped.get((*case, op))
        return statistics.median(getattr(m, metric) for m in runs) if runs else None

    def spread(self, case: Case, op: str) -> float | None:
        """How far ``case``'s ``op`` rate moved across the runs: ``max / min - 1``.

        ``None`` when fewer than two runs measured it, since one run has no spread.
        """
        runs = self._grouped.get((*case, op), [])
        rates = [m.ops_per_s for m in runs]
        if len(rates) < _SPREAD_MIN_RUNS or min(rates) <= 0:
            return None
        return max(rates) / min(rates) - 1

    def ratio(self, top: Case, bottom: Case, op: str, metric: str = 'ops_per_s') -> float | None:
        """``median(top) / median(bottom)`` for ``op``, or ``None`` if either is unmeasured.

        A ratio of medians, not a median of per-run ratios: each side is the
        middle of its own runs, as the tables quote it.
        """
        upper, lower = self.median(top, op, metric), self.median(bottom, op, metric)
        if upper is None or lower is None or lower == 0:
            return None
        return upper / lower


def _fmt(value: float | None, render: Callable[[float], str]) -> str:
    return _NA if value is None else render(value)


def _table(rows: list[list[str]]) -> str:
    """A padded Markdown table; the first row is the header."""
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]

    def line(cells: list[str]) -> str:
        return '| ' + ' | '.join(c.ljust(w) for c, w in zip(cells, widths, strict=True)) + ' |'

    rule = '|' + '|'.join('-' * (w + 2) for w in widths) + '|'
    return '\n'.join([line(rows[0]), rule, *(line(r) for r in rows[1:])])


def _columns(results: Results) -> list[tuple[str, str, str]]:
    return [c for c in _COLUMNS if results.has((c[0], c[1]))]


def _per_column(results: Results, cell: Callable[[Case, str], str]) -> str:
    """A table of one ``cell(case, op)`` per (op, column), headed by the columns."""
    columns = _columns(results)
    rows = [['Op', *(header for _, _, header in columns)]]
    rows.extend([op, *(cell((library, variant), op) for library, variant, _ in columns)] for op in _OPS)
    return _table(rows)


def ops_table(results: Results) -> str:
    """Median ``ops/s`` per (op, column), with the ``seared`` columns' ratio to the baseline."""

    def cell(case: Case, op: str) -> str:
        text = _fmt(results.median(case, op), lambda v: f'{v:,.0f} ops/s')
        ratio = results.ratio(case, _BASELINE, op)
        if case[0] == 'seared' and ratio is not None:
            text += f' (~{ratio:.1f}{_TIMES})'
        return text

    return _per_column(results, cell)


def us_table(results: Results) -> str:
    """Median microseconds per call, same layout as :func:`ops_table`."""
    return _per_column(results, lambda case, op: _fmt(results.median(case, op, 'us_per_op'), lambda v: f'{v:.1f} µs'))


def spread_table(results: Results) -> str:
    """How far each column's rate moved between runs, same layout; ``n/a`` for one run."""
    return _per_column(results, lambda case, op: _fmt(results.spread(case, op), lambda v: f'{v * 100:.1f}%'))


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
    results = Results(report)
    return {
        'ops': f'\n{ops_table(results)}\n',
        'us': f'\n{us_table(results)}\n',
        'spread': f'\n{spread_table(results)}\n',
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


def update(report: Report, *, check: bool = False, docs: Sequence[Path] = DOCS) -> list[Path]:
    """Re-render ``docs`` from ``report``; return the files that differed.

    With ``check=True`` nothing is written: the return value is the drift.
    """
    generated = blocks(report)
    drifted = []
    for path in docs:
        text = path.read_text(encoding='utf-8')
        new = render(text, generated)
        if new != text:
            drifted.append(path)
            if not check:
                path.write_text(new, encoding='utf-8')
    return drifted


def load(path: Path = RESULTS) -> Report:
    """The report at ``path``, the committed artifact by default."""
    return Report.from_json(path)


def main() -> None:
    """Re-render the docs' tables from the committed results, or check them."""
    parser = argparse.ArgumentParser(prog='python -m bench.tables', description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='exit 1 if a doc has drifted from results.json')
    args = parser.parse_args()

    drifted = update(load(), check=args.check)
    for path in drifted:
        print(f'{"drifted" if args.check else "updated"}: {path.relative_to(_ROOT)}')
    if args.check and drifted:
        sys.exit(1)


if __name__ == '__main__':
    main()
