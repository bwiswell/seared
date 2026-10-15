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
    # serialized (wire-invisible metadata, like ``data_key``); surfaced by
    # ``seared.doc`` in the generated schema pages, and available to any other
    # tooling through ``Cls.__seared_fields__``.
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
                'seared: `missing=` is deprecated; use `default=` (or `default_factory=` for mutable defaults).',
                DeprecationWarning,
                stacklevel=_caller_stacklevel(self),
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


def _caller_stacklevel(field: Field) -> int:
    """The ``stacklevel`` that pins a warning on whoever constructed ``field``.

    No fixed number is right: between the caller and ``__post_init__`` sit
    the dataclass-generated ``__init__`` plus whatever the concrete field
    adds (``T`` / ``Tuple`` define an ``__init__``, ``Enum`` a
    ``__post_init__``). Every one of those frames is a method of ``field``
    itself, so skip frames whose ``self`` *is* it; the first that isn't is
    the caller.
    """
    import inspect

    # ``currentframe()`` is this helper; one back is ``Field.__post_init__``,
    # the frame that calls ``warnings.warn`` and so ``stacklevel=1``.
    frame = inspect.currentframe()
    frame = frame.f_back if frame is not None else None
    level = 1
    while frame is not None and frame.f_locals.get('self') is field:
        frame = frame.f_back
        level += 1
    return level
