"""Pin: ``Decimal`` field — lossless string by default; opt-in
JSON-number form via ``as_number=True``."""
from __future__ import annotations

from decimal import Decimal as D
from typing import Optional

import pytest

import seared as s


@s.seared
class Money(s.Seared):
    amount: D = s.Decimal(required=True)


@s.seared
class MoneyNumber(s.Seared):
    amount: D = s.Decimal(required=True, as_number=True)


class TestStringDefault:
    def test_round_trip_preserves_string_form(self):
        m = Money(amount=D('12345.6789'))
        d = Money.dump(m)
        assert d == {'amount': '12345.6789'}
        loaded = Money.load(d)
        assert loaded.amount == D('12345.6789')

    def test_lossless_high_precision(self):
        # Beyond JSON-number precision (>17 sig digits).
        big = D('1.23456789012345678901234567890')
        m = Money(amount=big)
        d = Money.dump(m)
        assert d == {'amount': str(big)}
        loaded = Money.load(d)
        assert loaded.amount == big

    def test_serialize_rejects_non_decimal_when_validating(self):
        with pytest.raises(s.ValidationError, match='expected Decimal'):
            Money.dump(Money.__new__(Money).__class__(amount=12.34))   # type: ignore[arg-type]

    def test_deserialize_parses_int_string_float(self):
        # load coerces from any reasonable string-able form.
        for inp, expected in (
            ('1.5', D('1.5')),
            ('100', D('100')),
            ('0.000001', D('0.000001')),
        ):
            assert Money.load({'amount': inp}).amount == expected

    def test_deserialize_invalid_raises(self):
        with pytest.raises(s.ValidationError, match='cannot parse'):
            Money.load({'amount': 'not-a-decimal'})


class TestNumberOptIn:
    def test_serializes_as_float(self):
        m = MoneyNumber(amount=D('1.5'))
        d = MoneyNumber.dump(m)
        assert d == {'amount': 1.5}
        assert isinstance(d['amount'], float)

    def test_round_trip_through_float(self):
        m = MoneyNumber(amount=D('100.25'))
        loaded = MoneyNumber.load(MoneyNumber.dump(m))
        assert loaded.amount == D('100.25')

    def test_high_precision_loses_in_number_mode(self):
        """as_number=True is documented-lossy past float precision."""
        big = D('1.23456789012345678901234567890')
        m = MoneyNumber(amount=big)
        loaded = MoneyNumber.load(MoneyNumber.dump(m))
        # Lossy via float — round-trip != original beyond 17 digits.
        assert loaded.amount != big   # documented contract
