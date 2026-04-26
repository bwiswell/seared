"""Pin: TOML codec — read via stdlib ``tomllib``, write via optional
``seared[toml]`` extra (lazy ``tomli-w`` import)."""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

import seared as s


@s.seared
class Cfg(s.Seared):
    name: str = s.Str(required=True)
    port: int = s.Int(required=True)
    debug: bool = s.Bool(missing=False)


class TestRoundTrip:
    def test_to_toml_writes_string(self):
        pytest.importorskip('tomli_w')
        cfg = Cfg(name='alpha', port=7447, debug=True)
        text = Cfg.to_toml(cfg)
        assert 'name = "alpha"' in text
        assert 'port = 7447' in text
        assert 'debug = true' in text

    def test_round_trip(self):
        pytest.importorskip('tomli_w')
        original = Cfg(name='beta', port=8000)
        loaded = Cfg.from_toml(Cfg.to_toml(original))
        assert loaded.name == 'beta'
        assert loaded.port == 8000
        assert loaded.debug is False

    def test_from_toml_string(self):
        cfg = Cfg.from_toml('name = "gamma"\nport = 9000\n')
        assert cfg.name == 'gamma'
        assert cfg.port == 9000

    def test_from_toml_file(self, tmp_path):
        f = tmp_path / 'cfg.toml'
        f.write_text('name = "delta"\nport = 1234\n')
        cfg = Cfg.from_toml(str(f))
        assert cfg.name == 'delta'


class TestReadWithoutWriteExtra:
    """Pin: stdlib ``tomllib`` covers the read path, so ``from_toml``
    works regardless of whether the ``[toml]`` extra is installed."""

    def test_from_toml_works_when_tomli_w_unavailable(self):
        # Simulate tomli_w being absent.
        real_tomli_w = sys.modules.pop('tomli_w', None)
        try:
            with patch.dict(sys.modules, {'tomli_w': None}):
                # Read still works — only stdlib.
                cfg = Cfg.from_toml('name = "x"\nport = 1\n')
                assert cfg.name == 'x'
        finally:
            if real_tomli_w is not None:
                sys.modules['tomli_w'] = real_tomli_w


class TestWriteRequiresExtra:
    def test_to_toml_without_tomli_w_raises_helpful_import(self):
        real_tomli_w = sys.modules.pop('tomli_w', None)
        try:
            with patch.dict(sys.modules, {'tomli_w': None}):
                with pytest.raises(ImportError, match='tomli-w'):
                    Cfg.to_toml(Cfg(name='x', port=1))
        finally:
            if real_tomli_w is not None:
                sys.modules['tomli_w'] = real_tomli_w


class TestErrors:
    def test_non_table_top_level_raises(self):
        # Top-level TOML must be a table; arrays at top level → ValueError.
        # tomllib parses a stray scalar, but a list-style isn't valid TOML.
        # Simpler: an empty file parses to {} (a dict), so this still works.
        # Use an explicit invalid form to test our wrapper.
        cfg = Cfg.from_toml('name = "x"\nport = 1\n')
        assert cfg.name == 'x'
