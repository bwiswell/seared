"""Tests for ``seared.fields.union`` — the tagged-union ``UNWRAP`` field.

Folds in the ``default=<VariantCls>`` schema-evolution fallback suite
(was ``tests/test_union_fallback.py``).
"""

from __future__ import annotations

import pytest

import seared as s


@s.seared
class Start(s.Seared):
    speed: float = s.Float(required=True)


@s.seared
class Stop(s.Seared):
    pass


@s.seared
class Configure(s.Seared):
    mode: str = s.Str(required=True)


# ---------------------------------------------------------------------------
# Envelope shapes (nested vs flat).
# ---------------------------------------------------------------------------


class TestNestedEnvelope:
    def test_round_trip_start(self):
        @s.seared
        class Control(s.Seared):
            action: object = s.Union(
                variants={'start': Start, 'stop': Stop, 'configure': Configure},
                tag_key='action',
                payload_key='args',
                required=True,
            )

        ctrl = Control(action=Start(speed=10.0))
        d = Control.dump(ctrl)
        assert d == {'action': 'start', 'args': {'speed': 10.0}}

        loaded = Control.load(d)
        assert isinstance(loaded.action, Start)
        assert loaded.action.speed == 10.0

    def test_round_trip_stop(self):
        @s.seared
        class Control(s.Seared):
            action: object = s.Union(
                variants={'start': Start, 'stop': Stop},
                tag_key='action',
                payload_key='args',
                required=True,
            )

        d = Control.dump(Control(action=Stop()))
        assert d == {'action': 'stop', 'args': {}}
        loaded = Control.load(d)
        assert isinstance(loaded.action, Stop)


class TestFlatEnvelope:
    def test_round_trip_flat(self):
        @s.seared
        class Event(s.Seared):
            data: object = s.Union(
                variants={'start': Start, 'configure': Configure},
                tag_key='type',
                required=True,  # payload_key=None → flat
            )

        d = Event.dump(Event(data=Start(speed=5.0)))
        assert d == {'type': 'start', 'speed': 5.0}

        loaded = Event.load(d)
        assert isinstance(loaded.data, Start)
        assert loaded.data.speed == 5.0


# ---------------------------------------------------------------------------
# Strict tag/instance validation.
# ---------------------------------------------------------------------------


class TestUnknownTag:
    def test_unknown_tag_raises(self):
        @s.seared
        class Control(s.Seared):
            action: object = s.Union(
                variants={'start': Start, 'stop': Stop},
                tag_key='action',
                payload_key='args',
                required=True,
            )

        with pytest.raises(s.ValidationError, match='unknown tag'):
            Control.load({'action': 'boom', 'args': {}})

    def test_missing_tag_raises(self):
        @s.seared
        class Control(s.Seared):
            action: object = s.Union(
                variants={'start': Start},
                tag_key='action',
                payload_key='args',
                required=True,
            )

        with pytest.raises(s.ValidationError, match='missing tag'):
            Control.load({'args': {}})


class TestSerializeValidation:
    def test_wrong_instance_type_raises(self):
        @s.seared
        class Control(s.Seared):
            action: object = s.Union(
                variants={'start': Start},
                tag_key='action',
                payload_key='args',
                required=True,
            )

        class Unrelated:
            pass

        with pytest.raises(s.ValidationError, match='does not match'):
            Control.dump(Control(action=Unrelated()))


class TestWithOtherFields:
    def test_union_alongside_regular_fields(self):
        @s.seared
        class Command(s.Seared):
            issued_by: str = s.Str(required=True)
            action: object = s.Union(
                variants={'start': Start, 'stop': Stop},
                tag_key='action',
                payload_key='args',
                required=True,
            )

        cmd = Command(issued_by='alice', action=Start(speed=7.5))
        d = Command.dump(cmd)
        assert d == {
            'issued_by': 'alice',
            'action': 'start',
            'args': {'speed': 7.5},
        }
        loaded = Command.load(d)
        assert loaded.issued_by == 'alice'
        assert isinstance(loaded.action, Start)
        assert loaded.action.speed == 7.5


class TestMultipleUnwrapDisjointKeys:
    """0.1.9 relaxes the single-UNWRAP-per-class constraint when each
    Union's wire keys are disjoint. The collision-rejection side lives
    in ``tests/_core/test_decorator.py::TestKeyCollisionRejected``."""

    def test_two_unions_with_disjoint_keys_accepted(self):
        # Both Unions use distinct tag_key strings — no collision.
        @s.seared
        class Cmd(s.Seared):
            one: object = s.Union(
                variants={'a': Start},
                tag_key='k1',
                required=True,
            )
            two: object = s.Union(
                variants={'b': Stop},
                tag_key='k2',
                required=True,
            )

        cmd = Cmd(one=Start(speed=5.0), two=Stop())
        d = Cmd.dump(cmd)
        loaded = Cmd.load(d)
        assert isinstance(loaded.one, Start)
        assert isinstance(loaded.two, Stop)


# ---------------------------------------------------------------------------
# Schema-evolution fallback — ``default=<VariantCls>`` (was
# tests/test_union_fallback.py).
# ---------------------------------------------------------------------------


@s.seared
class _StartInt(s.Seared):
    speed: int = s.Int(required=True)


@s.seared
class _StopReason(s.Seared):
    reason: str = s.Str(missing='')


@s.seared
class Unknown(s.Seared):
    """Generic catch-all for variants the consumer doesn't yet know about."""

    raw_tag: str = s.Str(missing='')


class TestNoFallback:
    """Default behaviour — unknown tags raise."""

    def test_unknown_tag_raises(self):
        @s.seared
        class Cmd(s.Seared):
            action: object = s.Union(
                variants={'start': _StartInt, 'stop': _StopReason},
            )

        with pytest.raises(s.ValidationError, match='unknown tag'):
            Cmd.load({'type': 'reboot', 'speed': 0})


class TestWithFallback:
    """``default=<Variant>`` opts into graceful fallback."""

    def test_unknown_tag_coerces_to_default(self):
        @s.seared
        class Cmd(s.Seared):
            action: object = s.Union(
                variants={'start': _StartInt, 'stop': _StopReason},
                default=Unknown,
            )

        loaded = Cmd.load({'type': 'reboot', 'raw_tag': 'reboot'})
        assert isinstance(loaded.action, Unknown)

    def test_known_tags_still_route_correctly(self):
        @s.seared
        class Cmd(s.Seared):
            action: object = s.Union(
                variants={'start': _StartInt, 'stop': _StopReason},
                default=Unknown,
            )

        s_loaded = Cmd.load({'type': 'start', 'speed': 10})
        assert isinstance(s_loaded.action, _StartInt)
        assert s_loaded.action.speed == 10

        x_loaded = Cmd.load({'type': 'stop', 'reason': 'test'})
        assert isinstance(x_loaded.action, _StopReason)
        assert x_loaded.action.reason == 'test'

    def test_default_must_be_a_class(self):
        with pytest.raises(TypeError, match='default must be a class'):
            s.Union(
                variants={'start': _StartInt},
                default='not-a-class',  # type: ignore[arg-type]
            )

    def test_default_none_preserves_strict_behavior(self):
        @s.seared
        class Cmd(s.Seared):
            action: object = s.Union(
                variants={'start': _StartInt},
                default=None,
            )

        with pytest.raises(s.ValidationError, match='unknown tag'):
            Cmd.load({'type': 'reboot'})
