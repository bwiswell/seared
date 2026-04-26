"""``polars.DataFrame`` field — JSON-records wire form.

Mirrors the ``PandasFrame`` shape: list of records on the wire, polars
DataFrame in memory. ``polars.DataFrame.to_dicts()`` and the
``polars.DataFrame(records)`` constructor handle the round-trip.

Module name has a trailing underscore (``polars_.py``) to avoid
shadowing the upstream ``polars`` package on import. The field is
re-exported from ``seared.__init__`` as ``s.PolarsFrame``.
"""
from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from .._core.errors import ValidationError
from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class PolarsFrame(Field):
    """``polars.DataFrame`` ↔ list-of-records JSON wire form.

    ``many=True`` / ``keyed=True`` not supported (a field is one
    DataFrame). Wrap in a ``T(WrapperClass)`` for list-of-frames.
    """

    def __post_init__(self):
        if self.many or self.keyed:
            raise TypeError(
                'PolarsFrame: many=True / keyed=True not supported — '
                'wrap in a T(SomeWrapperClass) for list-of-frames.'
            )

    def serialize(self, value, validate: bool = True, **kwargs):
        if not isinstance(value, pl.DataFrame):
            if validate:
                raise ValidationError(
                    f'expected polars.DataFrame, got {type(value).__name__}'
                )
            return value
        return value.to_dicts()

    def deserialize(self, value, validate: bool = True, **kwargs):
        if isinstance(value, pl.DataFrame):
            return value
        if not isinstance(value, list):
            if validate:
                raise ValidationError(
                    f'expected list of records for PolarsFrame, '
                    f'got {type(value).__name__}'
                )
            return value
        # ``polars.DataFrame([{...}, ...])`` accepts a list of dicts
        # directly. Empty lists need an explicit schema=[] to avoid a
        # warning — handle the empty case specially.
        if not value:
            return pl.DataFrame()
        return pl.DataFrame(value)
