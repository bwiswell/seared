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

import csv as _csv
import io

from ._common import read_source


# Field type names that don't fit in a CSV cell. We check by the type's
# ``__name__`` rather than ``isinstance`` so that the optional dataframe
# fields (which may not even be installed) work without an import here.
_NESTING_FIELD_NAMES = frozenset({
    'T', 'Union', 'NDArray', 'Tuple',
    'PandasFrame', 'PolarsFrame',
})


def _validate_flat(cls):
    """Raise ``TypeError`` if any field on ``cls`` can't fit in a CSV cell.

    Checked at every ``to_csv`` / ``from_csv`` call (cheap — runs against
    the cached ``__seared_fields__`` tuple).
    """
    for attr, _, f in cls.__seared_fields__:
        type_name = type(f).__name__
        if type_name in _NESTING_FIELD_NAMES:
            raise TypeError(
                f'{cls.__name__}.{attr} is a {type_name} field — '
                f'CSV requires flat (non-nested) classes only'
            )
        if f.keyed or f.many:
            raise TypeError(
                f'{cls.__name__}.{attr}: CSV cells cannot hold '
                f'keyed/many collections'
            )


def to(cls, items) -> str:
    """Serialise an iterable of ``cls`` instances to CSV string content."""
    _validate_flat(cls)
    columns = [attr for attr, _, _ in cls.__seared_fields__]
    out = io.StringIO()
    writer = _csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    for item in items:
        writer.writerow(cls.dump(item))
    return out.getvalue()


def from_(cls, source) -> list:
    """Parse CSV ``source`` (path or string content) into ``list[cls]``."""
    _validate_flat(cls)
    text = read_source(source)
    reader = _csv.DictReader(io.StringIO(text))
    return [cls.load(row) for row in reader]
