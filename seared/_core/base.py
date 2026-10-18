from __future__ import annotations

import json

# At runtime, not under ``TYPE_CHECKING``: ``__seared_load__``'s annotation
# below names it, and ``typing.get_type_hints`` evaluates that on every
# subclass. In 0.4.1 and 0.4.2 it was imported for type checking only, and
# ``get_type_hints`` raised ``NameError`` on every seared class.
from collections.abc import Callable  # noqa: TC003
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple, Self

from .accel import AccelInfo

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable

    from seared.fields.field import Field

    from .unknown import Unknown


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

    #: What ``load`` does by default with a key the class doesn't declare:
    #: ``'ignore'`` or ``'raise'``, from ``@seared(unknown=…)`` (0.4.1).
    __seared_unknown__: ClassVar[str] = 'ignore'

    #: Internal: the class's load, ``(data, format) -> instance``, with no
    #: ``unknown=`` in front of it. A nested ``T`` or ``Union`` loads through it
    #: (see ``seared._core.unknown``). Set by the decorator.
    __seared_load__: ClassVar[Callable[[Any, str], Any]]

    @classmethod
    def dump(cls, obj: Seared, format: str = 'json') -> dict[str, Any]:
        """Instance → wire dict.

        ``format`` is the carrier hint threaded into every field (see
        ``_core.decorator``); ``Bytes`` emits native binary under
        ``'msgpack'``, ``T`` and ``Tuple`` pass it on, and the rest ignore it.

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
    def load(cls, data: dict[str, Any], format: str = 'json', unknown: Unknown | None = None) -> Self:
        """Wire dict → instance. ``format`` as in :meth:`dump`.

        ``unknown`` says what to do with a key the class doesn't declare:
        ``'ignore'`` drops it, ``'raise'`` refuses the load with a
        ``ValidationError`` naming every such key, and ``None`` (the default)
        takes the class's own ``@seared(unknown=…)``, which is ``'ignore'``
        unless it says otherwise. The refusal covers the whole input, nested
        classes included (see ``seared._core.unknown``).
        """
        raise NotImplementedError

    @classmethod
    def loads(cls, data: str, unknown: Unknown | None = None) -> Self:
        """JSON string → instance. ``unknown`` as in :meth:`load`."""
        return cls.load(json.loads(data), unknown=unknown)

    # Per-format codecs. Real implementations are attached at decorator
    # time (``seared/formats/_attach_format_methods``); these
    # declarations exist so the methods type-check on the base surface,
    # exactly like ``dump`` / ``load`` above.

    @classmethod
    def to_json(cls, obj: Seared, **kwargs: Any) -> str:
        raise NotImplementedError

    @classmethod
    def from_json(cls, source: str | os.PathLike, unknown: Unknown | None = None) -> Self:
        raise NotImplementedError

    @classmethod
    def to_toml(cls, obj: Seared) -> str:
        raise NotImplementedError

    @classmethod
    def from_toml(cls, source: str | os.PathLike, unknown: Unknown | None = None) -> Self:
        raise NotImplementedError

    @classmethod
    def to_yaml(cls, obj: Seared) -> str:
        raise NotImplementedError

    @classmethod
    def from_yaml(cls, source: str | os.PathLike, unknown: Unknown | None = None) -> Self:
        raise NotImplementedError

    @classmethod
    def to_csv(cls, items: Iterable[Seared]) -> str:
        raise NotImplementedError

    @classmethod
    def from_csv(cls, source: str | os.PathLike, unknown: Unknown | None = None) -> list[Self]:
        raise NotImplementedError
