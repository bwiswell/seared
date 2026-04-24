from __future__ import annotations

from datetime import date

import seared as s


class TestDate:
    def test_load_and_dump(self):
        @s.seared
        class Obj(s.Seared):
            d: date = s.Date(required=True)

        obj = Obj.load({'d': '2025-01-15'})
        assert obj.d == date(2025, 1, 15)
        dumped = Obj.dump(obj)
        assert dumped['d'] == '2025-01-15'

    def test_custom_format(self):
        @s.seared
        class Obj(s.Seared):
            d: date = s.Date(format='%Y%m%d', required=True)

        obj = Obj.load({'d': '20250115'})
        assert obj.d == date(2025, 1, 15)
        dumped = Obj.dump(obj)
        assert dumped['d'] == '20250115'

    def test_many_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            dates: list = s.Date(many=True, required=True)

        obj = Obj.load({'dates': ['2025-01-01', '2025-06-15']})
        assert obj.dates == [date(2025, 1, 1), date(2025, 6, 15)]
        d = Obj.dump(obj)
        assert d['dates'] == ['2025-01-01', '2025-06-15']
