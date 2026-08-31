"""Pin: ``PolarsFrame`` field — round-trip via JSON-records form."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

import seared as s

pl = pytest.importorskip('polars')


@s.seared
class Report(s.Seared):
    name: str = s.Str(required=True)
    data: pl.DataFrame = s.PolarsFrame(required=True)


class TestRoundTrip:
    def test_basic_round_trip(self):
        df = pl.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})
        r = Report(name='r1', data=df)
        d = Report.dump(r)
        # Wire form: list of records.
        assert d['data'] == [
            {'a': 1, 'b': 'x'},
            {'a': 2, 'b': 'y'},
            {'a': 3, 'b': 'z'},
        ]
        loaded = Report.load(d)
        assert isinstance(loaded.data, pl.DataFrame)
        # Polars DataFrame equality.
        assert loaded.data.equals(df)

    def test_empty_dataframe_round_trip(self):
        df = pl.DataFrame()
        r = Report(name='empty', data=df)
        d = Report.dump(r)
        assert d['data'] == []
        loaded = Report.load(d)
        assert len(loaded.data) == 0

    def test_via_to_json_method(self):
        df = pl.DataFrame({'x': [1.5, 2.5]})
        r = Report(name='via-json', data=df)
        encoded = Report.to_json(r)
        loaded = Report.from_json(encoded)
        assert loaded.data.equals(df)


class TestValidation:
    def test_serialize_rejects_non_dataframe(self):
        @s.seared
        class R(s.Seared):
            data: pl.DataFrame = s.PolarsFrame(required=True)

        bad = R.__new__(R)
        object.__setattr__(bad, 'data', 'not-a-dataframe')
        with pytest.raises(s.ValidationError, match=r'expected polars\.DataFrame'):
            R.dump(bad)


class TestManyKeyedRejected:
    def test_many_raises(self):
        with pytest.raises(TypeError, match='many=True'):
            s.PolarsFrame(many=True)

    def test_keyed_raises(self):
        with pytest.raises(TypeError, match='many=True'):
            s.PolarsFrame(keyed=True)


class TestMissingPolars:
    """Pin: graceful ``ImportError`` when polars isn't installed."""

    def test_helpful_import_error(self):
        real_polars = sys.modules.get('polars')
        try:
            with patch.dict(sys.modules, {'polars': None}):
                if 'seared.fields.polars_' in sys.modules:
                    del sys.modules['seared.fields.polars_']
                import importlib

                import seared as s_mod

                importlib.reload(s_mod)
                with pytest.raises(ImportError, match='polars'):
                    s_mod.PolarsFrame()
        finally:
            if real_polars is not None:
                sys.modules['polars'] = real_polars
            import importlib

            import seared as s_mod

            importlib.reload(s_mod)
