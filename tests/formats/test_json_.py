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


@s.seared
class Reading(s.Seared):
    sensor: str = s.Str(required=True)
    value: float | None = s.Float(nullable=True, required=True)
    unit: str = s.Str(default='C')


class TestNull:
    """Pin: a JSON ``null`` is a value only on a nullable field; elsewhere it reads as absent."""

    def test_a_null_on_a_nullable_field_is_kept(self):
        got = Reading.from_json('{"sensor": "t1", "value": null, "unit": null}')
        assert (got.value, got.unit) == (None, 'C')

    def test_a_null_on_a_required_field_is_missing(self):
        with pytest.raises(s.ValidationError, match=r'^Reading\.sensor: required key missing$'):
            Reading.from_json('{"sensor": null, "value": 1.5}')

    def test_a_nullable_none_round_trips(self):
        text = Reading.to_json(Reading(sensor='t1', value=None))
        assert json.loads(text) == {'sensor': 't1', 'value': None, 'unit': 'C'}
        assert Reading.from_json(text) == Reading(sensor='t1', value=None)


@s.seared(unknown='raise')
class StrictTelemetry(s.Seared):
    id: int = s.Int(required=True)


class TestUnknownKeys:
    """``from_json`` honours the class's ``unknown=`` and a call's own (0.4.1)."""

    def test_the_class_default_refuses(self):
        with pytest.raises(s.ValidationError, match=r'StrictTelemetry\.iid: unknown key'):
            StrictTelemetry.from_json('{"id": 1, "iid": 2}')

    def test_a_call_overrides_the_class(self):
        assert StrictTelemetry.from_json('{"id": 1, "iid": 2}', unknown='ignore') == StrictTelemetry(id=1)
        with pytest.raises(s.ValidationError, match='unknown key'):
            Telemetry.from_json('{"id": 1, "x": 0, "y": 0, "z": 0}', unknown='raise')

    def test_by_default_unknown_keys_are_ignored(self):
        assert Telemetry.from_json('{"id": 1, "x": 0, "y": 0, "z": 0}') == Telemetry(id=1, x=0.0, y=0.0)
