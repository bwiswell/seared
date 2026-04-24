from __future__ import annotations

from datetime import time

import seared as s


class TestTime:
    def test_load_and_dump(self):
        @s.seared
        class Obj(s.Seared):
            t: time = s.Time(required=True)

        obj = Obj.load({'t': '08:30:00'})
        assert obj.t == time(8, 30, 0)
        dumped = Obj.dump(obj)
        assert '08:30:00' in dumped['t']
