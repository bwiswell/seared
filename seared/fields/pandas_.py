"""``pandas.DataFrame`` field — JSON-records wire form.

Wire shape: ``[{col: val, ...}, ...]`` (pandas ``to_dict('records')`` /
``DataFrame.from_records``). Most portable of the round-trip options;
loses dtype information for anything JSON can't represent (datetime,
Categorical, etc.). For dtype-preserving wire transport, layer your
own Arrow / Parquet codec on top.

Module name has a trailing underscore (``pandas_.py``) to avoid
shadowing the upstream ``pandas`` package on import. The field is
re-exported from ``seared.__init__`` as ``s.PandasFrame``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from seared._core.errors import ValidationError

from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class PandasFrame(Field):
    """``pandas.DataFrame`` ↔ list-of-records JSON wire form.

    Use ``many=True`` is NOT supported — a field is one DataFrame.
    Wrap in a ``T(SomeWrapperClass)`` if you need a list-of-frames.
    """

    def __post_init__(self) -> None:
        """Reject ``many`` / ``keyed`` — one field holds exactly one frame."""
        super().__post_init__()
        if self.many or self.keyed:
            msg = (
                'PandasFrame: many=True / keyed=True not supported — wrap in a T(SomeWrapperClass) for list-of-frames.'
            )
            raise TypeError(msg)

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:
        """``pandas.DataFrame`` → list of record dicts."""
        if not isinstance(value, pd.DataFrame):
            if validate:
                msg = f'expected pandas.DataFrame, got {type(value).__name__}'
                raise ValidationError(msg)
            return value
        return value.to_dict(orient='records')

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:
        """List of record dicts → ``pandas.DataFrame``."""
        if isinstance(value, pd.DataFrame):
            return value
        if not isinstance(value, list):
            if validate:
                msg = f'expected list of records for PandasFrame, got {type(value).__name__}'
                raise ValidationError(msg)
            return value
        return pd.DataFrame.from_records(value)
