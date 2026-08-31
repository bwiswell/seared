"""Pin: ``PandasFrame`` field — round-trip via JSON-records form."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

import seared as s

pd = pytest.importorskip('pandas')


@s.seared
class Report(s.Seared):
    name: str = s.Str(required=True)
    data: pd.DataFrame = s.PandasFrame(required=True)


class TestRoundTrip:
    def test_basic_round_trip(self):
        df = pd.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})
        r = Report(name='r1', data=df)
        d = Report.dump(r)
        # Wire form: list of records.
        assert d['data'] == [
            {'a': 1, 'b': 'x'},
            {'a': 2, 'b': 'y'},
            {'a': 3, 'b': 'z'},
        ]
        loaded = Report.load(d)
        assert isinstance(loaded.data, pd.DataFrame)
        # Pandas DataFrame equality via `.equals`.
        assert loaded.data.equals(df)

    def test_empty_dataframe_round_trip(self):
        df = pd.DataFrame({'a': [], 'b': []})
        r = Report(name='empty', data=df)
        d = Report.dump(r)
        assert d['data'] == []
        loaded = Report.load(d)
        assert len(loaded.data) == 0

    def test_via_to_json_method(self):
        df = pd.DataFrame({'x': [1.5, 2.5]})
        r = Report(name='via-json', data=df)
        encoded = Report.to_json(r)
        loaded = Report.from_json(encoded)
        assert loaded.data.equals(df)


class TestValidation:
    def test_serialize_rejects_non_dataframe(self):
        @s.seared
        class R(s.Seared):
            data: pd.DataFrame = s.PandasFrame(required=True)

        bad = R.__new__(R)
        object.__setattr__(bad, 'data', 'not-a-dataframe')
        with pytest.raises(s.ValidationError, match=r'expected pandas\.DataFrame'):
            R.dump(bad)

    def test_deserialize_passes_through_existing_dataframe(self):
        existing = pd.DataFrame({'x': [1, 2]})
        loaded = Report.load({'name': 'pass', 'data': existing})
        # In-memory shortcut — same object reference allowed.
        assert isinstance(loaded.data, pd.DataFrame)


class TestManyKeyedRejected:
    """Pin: ``many=True`` / ``keyed=True`` not supported."""

    def test_many_raises_at_field_construction(self):
        with pytest.raises(TypeError, match='many=True'):
            s.PandasFrame(many=True)

    def test_keyed_raises_at_field_construction(self):
        with pytest.raises(TypeError, match='many=True'):
            s.PandasFrame(keyed=True)


class TestMissingPandas:
    """Pin: a graceful ``ImportError`` when pandas isn't installed."""

    def test_helpful_import_error(self):
        # Simulate pandas being absent. The class returned from the
        # graceful-degrade try/except in seared/__init__.py raises on
        # __init__ — we rebuild that branch by patching out pandas
        # before reimporting the module.
        real_pandas = sys.modules.get('pandas')
        real_pf_mod = sys.modules.pop('seared.fields.pandas_', None)
        try:
            with patch.dict(sys.modules, {'pandas': None}):
                # Reload the dataframe.pandas_ module — its top-level
                # `import pandas as pd` will fail.
                import importlib

                import seared as s_mod

                # Force reimport so the try/except in __init__ runs.
                if 'seared.fields.pandas_' in sys.modules:
                    del sys.modules['seared.fields.pandas_']
                # Reimport seared: the try/except produces the
                # placeholder PandasFrame.
                importlib.reload(s_mod)
                with pytest.raises(ImportError, match='pandas'):
                    s_mod.PandasFrame()
        finally:
            if real_pf_mod is not None:
                sys.modules['seared.fields.pandas_'] = real_pf_mod
            if real_pandas is not None:
                sys.modules['pandas'] = real_pandas
            # Reload seared once more so the package state matches reality.
            import importlib

            import seared as s_mod

            importlib.reload(s_mod)
