"""CSV codec — class-method-only.

A CSV file is a list of records (one row per dataclass instance). The
codec is class-level: ``Cls.from_csv(source) -> list[Cls]`` and
``Cls.to_csv(items) -> str``. Nested fields (``T``, ``Union``,
``NDArray``, ``Tuple``, ``PandasFrame``, ``PolarsFrame``) and
``many=True`` / ``keyed=True`` collections raise ``TypeError`` at call
time — CSV cells can't hold structured data, and flatten-and-rehydrate
is its own design problem deferred to a future release.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable

    from seared._core.base import Seared

import csv as _csv
import io

from seared._core.errors import ValidationError, add_location

from ._common import read_source

# Field type names that don't fit in a CSV cell. We check by the type's
# ``__name__`` rather than ``isinstance`` so that the optional dataframe
# fields (which may not even be installed) work without an import here.
_NESTING_FIELD_NAMES = frozenset(
    {
        'T',
        'Union',
        'NDArray',
        'Tuple',
        'PandasFrame',
        'PolarsFrame',
    }
)


def _validate_flat(cls: type[Seared]) -> None:
    """Raise ``TypeError`` if any field on ``cls`` can't fit in a CSV cell.

    Checked at every ``to_csv`` / ``from_csv`` call (cheap — runs against
    the cached ``__seared_fields__`` tuple).
    """
    for attr, _, f in cls.__seared_fields__:
        type_name = type(f).__name__
        if type_name in _NESTING_FIELD_NAMES:
            msg = f'{cls.__name__}.{attr} is a {type_name} field — CSV requires flat (non-nested) classes only'
            raise TypeError(msg)
        if f.keyed or f.many:
            msg = f'{cls.__name__}.{attr}: CSV cells cannot hold keyed/many collections'
            raise TypeError(msg)


def to(cls: type[Seared], items: Iterable[Seared]) -> str:
    """Serialise an iterable of ``cls`` instances to CSV string content.

    One column per field that ``dump`` writes, headed by its wire key, the
    name ``dump`` gives it and ``from_csv`` reads it back by. A ``dump=False``
    field gets no column. ``None`` is written as an empty cell, which is how
    CSV, having no null, says it.
    """
    _validate_flat(cls)
    columns = [wire for _, wire, f in cls.__seared_fields__ if f.dump]
    out = io.StringIO()
    writer = _csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    for i, item in enumerate(items):
        try:
            writer.writerow(cls.dump(item))
        except ValidationError as e:
            # The path addresses what the caller passed: a sequence of records.
            add_location(e, i)
            raise
    return out.getvalue()


def from_(cls: type[Seared], source: str | os.PathLike) -> list[Seared]:
    """Parse CSV ``source`` (path or string content) into ``list[cls]``.

    An empty cell is CSV's null, and a short row's missing cells are too:
    each reaches ``load`` as ``None``, so it takes the field's default (or
    stays ``None`` on a nullable field), and a required field raises. The
    cost is that an empty *string* can't round-trip: it shares the one empty
    value with ``None``.
    """
    _validate_flat(cls)
    text = read_source(source)
    reader = _csv.DictReader(io.StringIO(text))
    records = []
    for i, row in enumerate(reader):
        try:
            records.append(cls.load({k: None if v == '' else v for k, v in row.items()}))
        except ValidationError as e:
            # The record's 0-based index among the data rows, header not
            # counted: ``Cls[41].port`` is ``rows[41]['port']``.
            add_location(e, i)
            raise
    return records
