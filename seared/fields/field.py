from __future__ import annotations

import warnings
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
    # serialized (wire-invisible metadata, like ``data_key``); surfaced by the
    # schema-doc generator (``seared.doc``). See project-plans/03-schema-docgen.
    doc: str | None = None
    # Canonical default kwargs. ``default`` is a static value; ``default_factory``
    # is a zero-arg callable invoked per-instance by the decorator (the clean home
    # for mutable defaults). ``missing`` is the deprecated legacy alias for
    # ``default`` — kept working, but warns. The decorator/load path reads the
    # resolved value off ``missing``; ``__post_init__`` folds ``default`` into it.
    default: Any = None
    default_factory: Callable[[], Any] | None = None
    missing: Any = None

    def __post_init__(self) -> None:
        """Fold ``default=`` into ``missing``, warning on the deprecated alias."""
        # A factory wins and is resolved per-instance downstream — leave
        # ``missing`` untouched so the decorator knows to call the factory.
        if self.default_factory is not None:
            return
        if self.default is not None:
            object.__setattr__(self, 'missing', self.default)
        elif self.missing is not None:
            warnings.warn(
                'seared: `missing=` is deprecated; use `default=` '
                '(or `default_factory=` for mutable defaults).',
                DeprecationWarning,
                stacklevel=2,
            )

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
