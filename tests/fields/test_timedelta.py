from __future__ import annotations

from datetime import timedelta
from typing import Optional

import seared as s


class TestTimeDelta:
    def test_load(self):
        @s.seared
        class Obj(s.Seared):
            duration: timedelta = s.TimeDelta(required=True)

        obj = Obj.load({'duration': 3600.0})
        assert obj.duration == timedelta(hours=1)

    def test_dump(self):
        @s.seared
        class Obj(s.Seared):
            duration: timedelta = s.TimeDelta(required=True)

        d = Obj.dump(Obj(duration=timedelta(hours=1)))
        assert d == {'duration': 3600.0}

    def test_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            duration: timedelta = s.TimeDelta(required=True)

        raw = {'duration': 90.5}
        obj = Obj.load(raw)
        assert Obj.dump(obj) == raw

    def test_subsecond_precision(self):
        @s.seared
        class Obj(s.Seared):
            duration: timedelta = s.TimeDelta(required=True)

        obj = Obj.load({'duration': 1.5})
        assert obj.duration == timedelta(seconds=1, milliseconds=500)
        assert Obj.dump(obj) == {'duration': 1.5}

    def test_zero(self):
        @s.seared
        class Obj(s.Seared):
            duration: timedelta = s.TimeDelta(required=True)

        obj = Obj.load({'duration': 0.0})
        assert obj.duration == timedelta(0)
        assert Obj.dump(obj) == {'duration': 0.0}

    def test_optional_none_excluded_from_dump(self):
        @s.seared
        class Obj(s.Seared):
            duration: Optional[timedelta] = s.TimeDelta()

        d = Obj.dump(Obj(duration=None))
        assert 'duration' not in d

    def test_missing_default(self):
        @s.seared
        class Obj(s.Seared):
            duration: timedelta = s.TimeDelta(missing=timedelta(0))

        obj = Obj.load({})
        assert obj.duration == timedelta(0)

    def test_many_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            durations: list = s.TimeDelta(many=True, required=True)

        raw = {'durations': [60.0, 120.0, 3600.0]}
        obj = Obj.load(raw)
        assert obj.durations == [timedelta(minutes=1), timedelta(minutes=2), timedelta(hours=1)]
        assert Obj.dump(obj) == raw
