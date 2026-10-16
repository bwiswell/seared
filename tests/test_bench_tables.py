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
from bench.tables import (
    Results,
    _approx_gain,
    _approx_x,
    blocks,
    load,
    ops_table,
    render,
    run_line,
    spread_table,
    update,
)

_VERSION = '0.3.4'
_RUSTED_VERSION = '0.3.4/rusted 0.3.1'
MARSHMALLOW = ('marshmallow', 'default')
STRICT = ('seared', 'strict')
LAX = ('seared', 'lax')
PYDANTIC = ('pydantic', 'default')
RUSTED = ('seared+rusted', 'strict')


def _m(case: tuple[str, str], op: str, ops_per_s: float, run: int = 0, version: str = _VERSION) -> Measurement:
    library, variant = case
    return Measurement(
        library=library,
        variant=variant,
        version=version,
        op=op,
        ops_per_s=ops_per_s,
        us_per_op=1e6 / ops_per_s,
        run=run,
    )


def _case(
    case: tuple[str, str],
    load_rates: list[float],
    dump_rates: list[float] | None = None,
    version: str = _VERSION,
) -> list[Measurement]:
    """One case's load and dump measurements, one of each per run."""
    out = []
    for run, (load_rate, dump_rate) in enumerate(zip(load_rates, dump_rates or load_rates, strict=True)):
        out += [_m(case, 'load', load_rate, run, version), _m(case, 'dump', dump_rate, run, version)]
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


class TestProse:
    def test_the_headline_quotes_strict_not_lax(self):
        # Through 0.3.3 the README's hand-written 3.5 ratio was the lax
        # column's, presented as the default's. Strict is the default.
        rows = _case(MARSHMALLOW, [10_000.0]) + _case(STRICT, [33_000.0]) + _case(LAX, [35_000.0])
        assert blocks(_report(rows))['load-vs-marshmallow'] == '~3.3\N{MULTIPLICATION SIGN}'

    @pytest.mark.parametrize(
        ('ratio', 'expected'),
        [(4.94, '~4.9'), (5.0, '~5'), (9.14, '~9'), (11.35, '~11'), (2.18, '~2.2')],
    )
    def test_ratios_keep_a_decimal_only_below_five(self, ratio, expected):
        assert _approx_x(ratio) == f'{expected}\N{MULTIPLICATION SIGN}'

    def test_gains_are_whole_percentages(self):
        assert _approx_gain(1.129) == '~13%'
        assert _approx_gain(1.056) == '~6%'

    def test_a_missing_input_reads_na(self):
        out = blocks(_report(_case(STRICT, [30_000.0])))  # no comparators, no rusted
        for name in ('load-vs-marshmallow', 'pydantic-vs-seared', 'rusted-load', 'lax-load-gain', 'version-example'):
            assert out[name] == 'n/a', name
        assert _approx_x(None) == 'n/a'

    def test_one_run_says_so_and_has_no_spread(self):
        out = blocks(_report(_case(STRICT, [30_000.0])))
        assert out['runs'] == 'from one run'
        assert out['spread-max'] == 'n/a'

    def test_several_runs_quote_their_median_and_widest_spread(self):
        rows = _case(STRICT, [100.0, 130.0, 110.0]) + _case(MARSHMALLOW, [50.0, 52.0, 51.0])
        out = blocks(_report(rows, runs=3))
        assert out['runs'] == 'the median of three runs'
        assert out['spread-max'] == '~30%'

    def test_the_run_line_names_versions_and_runs(self):
        rows = _case(STRICT, [1.0]) + _case(RUSTED, [10.0], version=_RUSTED_VERSION)
        assert run_line(_report(rows)) == (
            '2026-10-16, Python 3.14.3, 20,000 iterations, one run; seared 0.3.4, rusted 0.3.1'
        )
        rows3 = _case(STRICT, [1.0, 1.0, 1.0])
        assert ', median of 3 runs; seared 0.3.4' in run_line(_report(rows3, runs=3))

    def test_the_version_example_is_a_code_span(self):
        rows = _case(STRICT, [1.0]) + _case(RUSTED, [10.0], version=_RUSTED_VERSION)
        assert blocks(_report(rows))['version-example'] == '`0.3.4/rusted 0.3.1`'


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
