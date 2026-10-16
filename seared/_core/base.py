from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple, Self

from .accel import AccelInfo

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable

    from seared.fields.field import Field


class FieldSpec(NamedTuple):
    """One declared field, as ``__seared_fields__`` lists it.

    Still the ``(attr, wire, field)`` triple it always was, so unpacking keeps
    working; the names and types are for tooling that reads one entry at a
    time, and for a checker, which can now see ``field`` is a ``Field``.
    """

    #: The Python attribute name.
    attr: str
    #: The key on the wire: ``data_key`` when set, else ``attr``.
    wire: str
    #: The declared field instance.
    field: Field


class Seared:
    #: One :class:`FieldSpec` per declared field, in order. Set by the
    #: decorator; ``()`` on an undecorated subclass.
    __seared_fields__: ClassVar[tuple[FieldSpec, ...]] = ()

    #: Whether a compiled accelerator took this class, and the reason if not
    #: (see ``_core.accel``). Declared here, rather than only assigned at
    #: decoration time, so that reading it type-checks — it is a documented
    #: introspection surface, and an attribute a checker can't see is one
    #: callers have to work around.
    __seared_accel__: ClassVar[AccelInfo] = AccelInfo(
        accelerated=False,
        reason='class is not decorated with @seared',
    )

    @classmethod
    def dump(cls, obj: Seared, format: str = 'json') -> dict[str, Any]:
        """Instance → wire dict.

        ``format`` is the carrier hint threaded into every field (see
        ``_core.decorator``); ``Bytes`` and ``NDArray`` emit native binary
        under ``'msgpack'``, and the rest ignore it.

        This declaration and the implementation the decorator attaches must
        stay signature-identical — ``tests/_core/test_base.py`` asserts it.
        """
        raise NotImplementedError

    @classmethod
    def dumps(cls, obj: Seared, **kwargs: Any) -> str:
        """Instance → JSON string.

        ``**kwargs`` pass through to ``json.dumps``, as they do for
        ``to_json``. ``allow_nan=False`` is the one to know: by default a
        ``NaN`` or ``inf`` float is written as a bare ``NaN`` / ``Infinity``,
        which Python reads back but standard JSON parsers (browsers
        included) refuse, and with it ``dumps`` raises ``ValueError``
        instead.
        """
        return json.dumps(cls.dump(obj), **kwargs)

    @classmethod
    def load(cls, data: dict[str, Any], format: str = 'json') -> Self:
        """Wire dict → instance. ``format`` as in :meth:`dump`."""
        raise NotImplementedError

    @classmethod
    def loads(cls, data: str) -> Self:
        return cls.load(json.loads(data))

    # Per-format codecs. Real implementations are attached at decorator
    # time (``seared/formats/_attach_format_methods``); these
    # declarations exist so the methods type-check on the base surface,
    # exactly like ``dump`` / ``load`` above.

    @classmethod
    def to_json(cls, obj: Seared, **kwargs: Any) -> str:
        raise NotImplementedError

    @classmethod
    def from_json(cls, source: str | os.PathLike) -> Self:
        raise NotImplementedError

    @classmethod
    def to_toml(cls, obj: Seared) -> str:
        raise NotImplementedError

    @classmethod
    def from_toml(cls, source: str | os.PathLike) -> Self:
        raise NotImplementedError

    @classmethod
    def to_yaml(cls, obj: Seared) -> str:
        raise NotImplementedError

    @classmethod
    def from_yaml(cls, source: str | os.PathLike) -> Self:
        raise NotImplementedError

    @classmethod
    def to_csv(cls, items: Iterable[Seared]) -> str:
        raise NotImplementedError

    @classmethod
    def from_csv(cls, source: str | os.PathLike) -> list[Self]:
        raise NotImplementedError
