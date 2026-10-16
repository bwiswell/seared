"""Pin: YAML codec — both directions via the optional ``seared[yaml]``
extra (lazy ``PyYAML`` import)."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

import seared as s


@s.seared
class Cfg(s.Seared):
    name: str = s.Str(required=True)
    items: list = s.Str(many=True, default=[])


class TestRoundTrip:
    def test_to_yaml(self):
        pytest.importorskip('yaml')
        cfg = Cfg(name='alpha', items=['x', 'y', 'z'])
        text = Cfg.to_yaml(cfg)
        # Roundtrip is the canonical check; explicit string check is
        # brittle to PyYAML version drift on quoting style.
        loaded = Cfg.from_yaml(text)
        assert loaded.name == 'alpha'
        assert loaded.items == ['x', 'y', 'z']

    def test_from_yaml_string(self):
        pytest.importorskip('yaml')
        text = 'name: gamma\nitems:\n  - one\n  - two\n'
        cfg = Cfg.from_yaml(text)
        assert cfg.name == 'gamma'
        assert cfg.items == ['one', 'two']

    def test_from_yaml_file(self, tmp_path):
        pytest.importorskip('yaml')
        f = tmp_path / 'cfg.yaml'
        f.write_text('name: from-file\nitems: []\n')
        cfg = Cfg.from_yaml(str(f))
        assert cfg.name == 'from-file'


class TestRequiresExtra:
    def test_without_pyyaml_raises_helpful_import(self):
        real_yaml = sys.modules.pop('yaml', None)
        try:
            with patch.dict(sys.modules, {'yaml': None}):
                with pytest.raises(ImportError, match='PyYAML'):
                    Cfg.to_yaml(Cfg(name='x'))
                with pytest.raises(ImportError, match='PyYAML'):
                    Cfg.from_yaml('name: x\n')
        finally:
            if real_yaml is not None:
                sys.modules['yaml'] = real_yaml


class TestErrors:
    def test_non_mapping_top_level_raises(self):
        pytest.importorskip('yaml')
        with pytest.raises(ValueError, match='must be a mapping'):
            Cfg.from_yaml('- a\n- list\n')


@s.seared
class Proxied(s.Seared):
    name: str = s.Str(default='anon')
    proxy: str | None = s.Str(nullable=True, default='direct')


class TestNull:
    """Pin: YAML's ``~`` / ``null`` follows JSON's ``null``."""

    def test_a_null_reads_as_absent_unless_nullable(self):
        pytest.importorskip('yaml')
        got = Proxied.from_yaml('name: ~\nproxy: ~\n')
        assert (got.name, got.proxy) == ('anon', None)

    def test_a_nullable_none_is_written_as_null(self):
        pytest.importorskip('yaml')
        text = Proxied.to_yaml(Proxied(proxy=None))
        assert 'proxy: null' in text
        assert Proxied.from_yaml(text).proxy is None
