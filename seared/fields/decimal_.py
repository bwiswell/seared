"""``decimal.Decimal`` field — lossless string by default.

The stdlib module is ``decimal``; we name this module ``decimal_`` (with
trailing underscore) to avoid shadowing it. The class is exported as
``Decimal`` from the ``seared`` package.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal as _Decimal, InvalidOperation

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Decimal(Field):
    """``decimal.Decimal`` serialised as a lossless string by default.

    String form preserves every digit — the safer default for financial
    / scientific data. ``as_number=True`` opts into JSON-number-style
    output (``float`` on serialise; ``Decimal`` on deserialise), which
    is lossy for values exceeding JSON-number precision (~15-17 digits
    via IEEE 754 double). Use the default unless you specifically need
    JSON-native numeric typing on the wire.
    """
    as_number: bool = False

    def serialize(self, value, validate: bool = True, **kwargs):
        if not isinstance(value, _Decimal):
            if validate:
                raise ValidationError(
                    f'expected Decimal, got {type(value).__name__}'
                )
            return value
        if self.as_number:
            return float(value)
        return str(value)

    def deserialize(self, value, validate: bool = True, **kwargs) -> _Decimal:
        if isinstance(value, _Decimal):
            return value
        try:
            return _Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as e:
            if validate:
                raise ValidationError(
                    f'cannot parse {value!r} as Decimal: {e}'
                ) from e
            return value
