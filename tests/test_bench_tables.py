"""Tests for ``bench/tables.py``: the generated benchmark tables.

``bench/`` is repo-only, not part of the package. ``python -m bench.tables
--check`` proves the docs match the artifact; it can't prove the medians and
ratios behind them are right. These pin that on synthetic reports, and that
the committed one-run artifact still renders exactly as it did before runs.
"""

from __future__ import annotations

import json
import statistics

import pytest

from bench.harness import Measurement, Report
from bench.tables import Results, blocks, load, ops_table, render, spread_table, update

_VERSION = '0.3.4'
MARSHMALLOW = ('marshmallow', 'default')
STRICT = ('seared', 'strict')
PYDANTIC = ('pydantic', 'default')


def _m(case: tuple[str, str], op: str, ops_per_s: float, run: int = 0) -> Measurement:
    library, variant = case
    return Measurement(
        library=library,
        variant=variant,
        version=_VERSION,
        op=op,
        ops_per_s=ops_per_s,
        us_per_op=1e6 / ops_per_s,
        run=run,
    )


def _case(case: tuple[str, str], load_rates: list[float], dump_rates: list[float] | None = None) -> list[Measurement]:
    """One case's load and dump measurements, one of each per run."""
    out = []
    for run, (load_rate, dump_rate) in enumerate(zip(load_rates, dump_rates or load_rates, strict=True)):
        out += [_m(case, 'load', load_rate, run), _m(case, 'dump', dump_rate, run)]
    return out


def _report(measurements: list[Measurement], runs: int = 1) -> Report:
    return Report(
        timestamp='2026-10-16T12:00:00+00:00',
        python='3.14.3',
        platform='Linux',
        iterations=20_000,
        runs=runs,
        measurements=measurements,
    )


class TestAggregation:
    def test_median_and_spread_over_runs(self):
        r = Results(_report(_case(STRICT, [130.0, 100.0, 110.0]), runs=3))
        assert r.median(STRICT, 'load') == 110.0
        assert r.spread(STRICT, 'load') == pytest.approx(0.3)

    def test_a_ratio_is_a_ratio_of_medians(self):
        # Medians 100 and 50 give 2.0; the median of the per-run ratios
        # (10/50, 100/40, 200/60) would be 2.5 instead.
        rows = _case(STRICT, [10.0, 100.0, 200.0]) + _case(MARSHMALLOW, [50.0, 40.0, 60.0])
        r = Results(_report(rows, runs=3))
        assert r.ratio(STRICT, MARSHMALLOW, 'load') == pytest.approx(2.0)

    def test_one_run_has_no_spread(self):
        r = Results(_report(_case(STRICT, [100.0])))
        assert r.median(STRICT, 'load') == 100.0
        assert r.spread(STRICT, 'load') is None

    def test_an_odd_run_count_keeps_the_two_tables_in_step(self):
        # With an odd count the median run is one actual run, so the median
        # µs/op is exactly 1e6 over the median ops/s; the committed artifact
        # records three runs for that reason.
        rates = [21_000.0, 30_000.0, 26_500.0]
        r = Results(_report(_case(STRICT, rates), runs=3))
        assert r.median(STRICT, 'load', 'us_per_op') == pytest.approx(1e6 / statistics.median(rates))

    def test_unmeasured_cases_give_none(self):
        r = Results(_report(_case(STRICT, [1.0])))
        assert not r.has(PYDANTIC)
        assert r.median(PYDANTIC, 'load') is None
        assert r.spread(PYDANTIC, 'load') is None
        assert r.ratio(STRICT, PYDANTIC, 'load') is None


class TestTables:
    def test_cells_are_medians_and_seared_carries_its_ratio(self):
        rows = _case(MARSHMALLOW, [8_000.0, 9_000.0, 10_000.0]) + _case(STRICT, [27_000.0, 30_000.0, 33_000.0])
        table = ops_table(Results(_report(rows, runs=3)))
        assert '| 9,000 ops/s ' in table
        assert '| 30,000 ops/s (~3.3\N{MULTIPLICATION SIGN}) ' in table

    def test_only_seared_columns_carry_a_ratio(self):
        rows = _case(MARSHMALLOW, [10_000.0]) + _case(PYDANTIC, [150_000.0])
        table = ops_table(Results(_report(rows)))
        assert '150,000 ops/s ' in table
        assert '(~' not in table

    def test_a_missing_comparator_drops_its_column_and_its_ratios(self):
        table = ops_table(Results(_report(_case(STRICT, [30_000.0]))))
        assert '`marshmallow`' not in table
        assert '`pydantic`' not in table
        assert '30,000 ops/s ' in table
        assert '(~' not in table  # nothing to quote it against

    def test_the_spread_table_reads_na_for_one_run(self):
        table = spread_table(Results(_report(_case(STRICT, [100.0]))))
        assert table.count('n/a') == 2  # load and dump

    def test_the_spread_table_reads_a_percentage_for_several_runs(self):
        table = spread_table(Results(_report(_case(STRICT, [100.0, 130.0, 110.0]), runs=3)))
        assert '30.0%' in table


class TestRendering:
    def test_only_marker_bodies_change(self):
        report = _report(_case(STRICT, [30_000.0]))
        text = 'Recorded <!-- bench:run -->stale<!-- /bench:run --> on a quiet box.'
        rendered = render(text, blocks(report))
        assert rendered.startswith('Recorded <!-- bench:run -->2026-10-16, Python 3.14.3')
        assert rendered.endswith('<!-- /bench:run --> on a quiet box.')
        assert 'stale' not in rendered

    def test_an_unknown_marker_raises(self):
        with pytest.raises(KeyError):
            render('<!-- bench:nope -->x<!-- /bench:nope -->', blocks(_report(_case(STRICT, [1.0]))))

    def test_check_reports_drift_and_writes_nothing(self, tmp_path):
        doc = tmp_path / 'doc.md'
        doc.write_text('<!-- bench:run -->stale<!-- /bench:run -->\n', encoding='utf-8')
        report = _report(_case(STRICT, [1.0]))
        assert update(report, check=True, docs=[doc]) == [doc]
        assert 'stale' in doc.read_text(encoding='utf-8')
        assert update(report, docs=[doc]) == [doc]
        assert update(report, check=True, docs=[doc]) == []


class TestArtifactCompatibility:
    def test_an_artifact_from_before_runs_loads_as_one_run(self):
        legacy = {
            'timestamp': '2026-08-31T18:19:21+00:00',
            'python': '3.14.3',
            'platform': 'Linux',
            'iterations': 20_000,
            'measurements': [
                {
                    'library': 'seared',
                    'variant': 'strict',
                    'version': '0.3.0',
                    'op': 'load',
                    'ops_per_s': 28_912.5,
                    'us_per_op': 34.6,
                }
            ],
        }
        report = Report.loads(json.dumps(legacy))
        assert report.runs == 1
        assert [m.run for m in report.measurements] == [0]

    def test_the_committed_artifact_renders_the_docs_unchanged(self):
        # Whatever the artifact holds, the docs' generated blocks match it; for
        # a one-run artifact that also proves the medians reproduce its values.
        assert update(load(), check=True) == []
