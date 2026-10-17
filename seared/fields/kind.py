"""A field's kind: which of seared's built-in fields it is (0.4.2).

Code that maps fields onto something else asks this: a JSON Schema emitter, a
column-type table, a check that a value fits in one key segment. Asking
``type(field).__name__`` misses a subclass, so a field that subclasses ``Str``
to check more fell out of every such table. :func:`field_kind` answers through
the class hierarchy instead: each built-in field class names its kind in a
``KIND`` class attribute, and a subclass inherits it.

A subclass that changes its base's wire form, rather than only checking more,
names its own kind (``KIND = FieldKind.STR``), or ``KIND = None`` for none. A
class that subclasses ``Field`` directly has none until it names one.

The accelerator reads the same attribute, but only off the exact built-in
class: a subclass's override would never run on the compiled path, so a
subclass declines acceleration whatever its kind (``seared._core.accel``).
"""

from __future__ import annotations

from enum import StrEnum


class FieldKind(StrEnum):
    """The kind of each built-in field class, one per class.

    The values are the accelerator spec's kind names (``T`` is ``nested``), so
    there is one vocabulary for both.
    """

    INT = 'int'
    FLOAT = 'float'
    STR = 'str'
    BOOL = 'bool'
    NESTED = 'nested'
    UUID = 'uuid'
    DATE = 'date'
    DATETIME = 'datetime'
    TIME = 'time'
    TIMEDELTA = 'timedelta'
    DECIMAL = 'decimal'
    BYTES = 'bytes'
    ENUM = 'enum'
    PATH = 'path'
    DICT = 'dict'
    TUPLE = 'tuple'
    UNION = 'union'
    NDARRAY = 'ndarray'
    PANDAS = 'pandas'
    POLARS = 'polars'


def field_kind(field: object) -> FieldKind | None:
    """The kind of ``field``, a field or a field class, or ``None`` when it has none.

    A subclass of a built-in field has its base's kind unless it names its own
    (``KIND``). Anything that isn't a field has none.

    Args:
        field: A field, such as one from ``Cls.__seared_fields__``, or a field
            class.

    Returns:
        The field's :class:`FieldKind`, or ``None``.
    """
    cls = field if isinstance(field, type) else type(field)
    kind = getattr(cls, 'KIND', None)
    return kind if isinstance(kind, FieldKind) else None


__all__ = ['FieldKind', 'field_kind']
