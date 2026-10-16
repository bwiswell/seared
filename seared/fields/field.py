from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, kw_only=True, slots=True)
class Field:
    data_key: str | None = None
    keyed: bool = False
    many: bool = False
    required: bool = False
    dump: bool = True
    # Human-facing field description — units, semantics, provenance. Never
    # serialized (wire-invisible metadata, like ``data_key``); surfaced by
    # ``seared.doc`` in the generated schema pages, and available to any other
    # tooling through ``Cls.__seared_fields__``.
    doc: str | None = None
    # The value an absent key gets. ``default`` is a static value, read as-is by
    # construction, ``load`` and the accelerator spec; ``default_factory`` is a
    # zero-arg callable invoked per instance (the clean home for mutable
    # defaults), and wins when both are set. ``missing=``, the alias these
    # replaced, was removed in 0.4.0.
    default: Any = None
    default_factory: Callable[[], Any] | None = None

    def __post_init__(self) -> None:
        """Nothing to resolve; kept so a subclass's ``super().__post_init__()`` still works."""

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:
        """Python value → JSON-safe value. Override in subclasses.

        ``**kwargs`` carries optional codec hints (e.g. ``format='msgpack'``)
        that fields supporting native binary representations (``Bytes``,
        ``NDArray``) can act on. Most fields ignore them — the wire shape
        is the same regardless of carrier format.
        """
        raise NotImplementedError

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:
        """JSON-safe value → Python value. Override in subclasses.

        Optional ``format=`` kwarg parallels :meth:`serialize`.
        """
        raise NotImplementedError
