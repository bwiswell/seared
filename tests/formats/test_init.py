"""Tests for ``seared.formats`` — the codec orchestrator. Pins that
``_attach_format_methods`` wires up the eight per-format classmethods
on every ``@s.seared`` class.
"""
from __future__ import annotations

import seared as s
from seared.formats import _attach_format_methods


@s.seared
class Sample(s.Seared):
    x: int = s.Int(required=True)
    name: str = s.Str(required=True)


class TestAttachedMethods:
    """Pin: every ``@s.seared`` class ships eight codec methods —
    ``to_*`` and ``from_*`` for each of json / toml / yaml / csv."""
    def test_to_json_attached(self):
        assert callable(Sample.to_json)

    def test_from_json_attached(self):
        assert callable(Sample.from_json)

    def test_to_toml_attached(self):
        assert callable(Sample.to_toml)

    def test_from_toml_attached(self):
        assert callable(Sample.from_toml)

    def test_to_yaml_attached(self):
        assert callable(Sample.to_yaml)

    def test_from_yaml_attached(self):
        assert callable(Sample.from_yaml)

    def test_to_csv_attached(self):
        assert callable(Sample.to_csv)

    def test_from_csv_attached(self):
        assert callable(Sample.from_csv)


class TestAttachReentrant:
    """Pin: calling ``_attach_format_methods`` twice doesn't break
    anything — each call simply rebinds the classmethods."""
    def test_double_attach_safe(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True)

        _attach_format_methods(Foo)
        # Still works after re-attachment.
        f = Foo(x=7)
        assert Foo.to_json(f) == '{"x": 7}'


class TestSmokeRoundTrip:
    """Light end-to-end check that the wiring leads to working codecs;
    deep per-codec testing lives in the dedicated ``test_<codec>.py``
    files alongside this one."""
    def test_json_round_trip(self):
        f = Sample(x=1, name='alice')
        encoded = Sample.to_json(f)
        loaded = Sample.from_json(encoded)
        assert loaded.x == 1
        assert loaded.name == 'alice'
