from __future__ import annotations

from datetime import datetime

import seared as s


class TestDateTime:
    def test_load_and_dump(self):
        @s.seared
        class Obj(s.Seared):
            ts: datetime = s.DateTime(required=True)

        obj = Obj.load({'ts': '2025-01-15T08:30:00'})
        assert obj.ts == datetime(2025, 1, 15, 8, 30, 0)
        dumped = Obj.dump(obj)
        assert '2025-01-15' in dumped['ts']
