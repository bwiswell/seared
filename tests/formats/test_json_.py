"""Pin: ``Cls.to_json`` / ``Cls.from_json`` are auto-attached to every
``@s.seared`` class. Stdlib-only — always available."""

from __future__ import annotations

import json

import pytest

import seared as s


@s.seared
class Telemetry(s.Seared):
    id: int = s.Int(required=True)
    x: float = s.Float(required=True)
    y: float = s.Float(required=True)


class TestRoundTrip:
    def test_basic(self):
        t = Telemetry(id=1, x=1.0, y=2.0)
        encoded = Telemetry.to_json(t)
        # Parses back via stdlib json — proves valid JSON.
        assert json.loads(encoded) == {'id': 1, 'x': 1.0, 'y': 2.0}

    def test_round_trip_through_string(self):
        original = Telemetry(id=7, x=3.14, y=2.71)
        loaded = Telemetry.from_json(Telemetry.to_json(original))
        assert loaded.id == 7
        assert loaded.x == 3.14
        assert loaded.y == 2.71

    def test_indent_pretty_printing(self):
        t = Telemetry(id=1, x=0.0, y=0.0)
        pretty = Telemetry.to_json(t, indent=2)
        assert '\n' in pretty
        assert '  "id": 1' in pretty


class TestPathDetection:
    def test_from_json_reads_file_path(self, tmp_path):
        f = tmp_path / 'tele.json'
        f.write_text('{"id": 42, "x": 1.0, "y": 2.0}')
        t = Telemetry.from_json(str(f))
        assert t.id == 42

    def test_from_json_parses_string_content(self):
        t = Telemetry.from_json('{"id": 99, "x": 0.0, "y": 0.0}')
        assert t.id == 99


class TestErrors:
    def test_invalid_json_raises_decode_error(self):
        with pytest.raises(json.JSONDecodeError):
            Telemetry.from_json('{not json')

    def test_non_dict_top_level_raises(self):
        with pytest.raises(ValueError, match='must be an object'):
            Telemetry.from_json('[1, 2, 3]')

    def test_missing_required_field_raises_validation(self):
        with pytest.raises(s.ValidationError):
            Telemetry.from_json('{"id": 1}')  # missing x, y
