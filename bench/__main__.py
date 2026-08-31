"""Bench runner. From the repo root: ``uv run python -m bench``.

Prints a results table and (unless ``--no-write``) records the run to
``bench/results.json`` — the committed artifact behind
``docs/overview/benchmarks.md``.
"""

from __future__ import annotations

import argparse
import importlib
from datetime import UTC, datetime
from pathlib import Path

from .harness import DEFAULT_ITERATIONS, Report, environment, payload, run_case

_SUITES = ['suite_seared', 'suite_marshmallow', 'suite_pydantic']
_DEFAULT_OUT = Path(__file__).parent / 'results.json'


def _collect_cases() -> list:
    cases = []
    for name in _SUITES:
        try:
            module = importlib.import_module(f'.{name}', package=__package__)
        except ImportError as exc:
            print(f'{name}: skipped ({exc.name} not installed — `uv sync --extra bench` to include comparators)')
            continue
        cases.extend(module.cases())
    return cases


def main() -> None:
    """Parse args, run every discovered suite, print and write the results."""
    parser = argparse.ArgumentParser(prog='python -m bench', description=__doc__.splitlines()[0])
    parser.add_argument(
        '-n',
        '--iterations',
        type=int,
        default=DEFAULT_ITERATIONS,
        help=f'iterations per (case, op) (default: {DEFAULT_ITERATIONS})',
    )
    parser.add_argument('--out', type=Path, default=_DEFAULT_OUT, help=f'results JSON path (default: {_DEFAULT_OUT})')
    parser.add_argument('--no-write', action='store_true', help='print the table only; do not write the JSON artifact')
    args = parser.parse_args()

    data = payload()
    measurements = []
    for case in _collect_cases():
        for m in run_case(case, data, args.iterations):
            measurements.append(m)
            print(f'{m.library:<12} {m.variant:<7} {m.op:<5} {m.ops_per_s:>10,.0f} ops/s  ({m.us_per_op:6.2f} us/op)')

    python, plat = environment()
    report = Report(
        timestamp=datetime.now(UTC).isoformat(timespec='seconds'),
        python=python,
        platform=plat,
        iterations=args.iterations,
        measurements=measurements,
    )
    if args.no_write:
        return
    args.out.write_text(Report.to_json(report, indent=2) + '\n')
    print(f'\nwrote {args.out}')


if __name__ == '__main__':
    main()
