"""Unknown keys: what a wire dict holds that its class doesn't declare (0.4.1).

``load`` reads the keys a class declares and ignores the rest. On the wire that
tolerance is load-bearing: a subscriber on an older version reads a newer
publisher's payload by ignoring the fields it doesn't know yet. For a config
file, or any input a person or an agent wrote, it hides a typo instead: the
misspelt key is dropped, and its setting keeps its default.

:func:`unknown_keys` reports those keys without raising, by walking the data
against the class tree.

What counts as known, at each level:

- each declared field's wire key (``data_key`` when set);
- each ``Union`` envelope's ``tag_key``, and its ``payload_key`` or, in a flat
  envelope, the selected variant's own keys.

Below a declared field the walk descends into ``T`` targets (element by
element for ``many``, value by value for ``keyed``) and into ``Tuple`` slots.
``Dict`` values, arrays and frames are data rather than schema, so their keys
are never reported. Nor are keys the class can't account for:

- an envelope routed to its ``fallback=`` variant, which exists to accept a
  variant this version doesn't know;
- a flat envelope whose tag is missing or unknown, which ``load`` refuses with
  an error of its own.

A value of the wrong type isn't the walk's concern either: ``load`` reports it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .errors import PathSegment


def unknown_keys(cls: type, data: Any) -> list[tuple[PathSegment, ...]]:
    """The path of every key in ``data`` that ``cls`` doesn't declare.

    Paths use ``load``'s vocabulary (wire keys, list indices, keyed-dict keys),
    so ``functools.reduce(operator.getitem, path, data)`` retrieves the value
    under each. They come depth-first, in the input's order. ``data`` that
    isn't a dict has no keys to report: ``load`` refuses it on its own.

    Never raises for what ``data`` holds, and never changes it: it's a report.
    The ``unknown='raise'`` option (on ``@seared``, ``load`` and the ``from_*``
    readers) refuses a load on the strength of it.

    Args:
        cls: A ``@seared`` class.
        data: A wire dict, as ``cls.load`` would take it.

    Returns:
        One path per unknown key; empty when every key is known.

    Raises:
        TypeError: If ``cls`` isn't a ``@seared`` class.
    """
    if getattr(cls, '__seared_fields__', None) is None:
        msg = f'unknown_keys: {cls!r} is not a @seared class'
        raise TypeError(msg)
    found: list[tuple[PathSegment, ...]] = []
    _walk(cls, data, (), found)
    return found


def _walk(cls: type, data: Any, path: tuple[PathSegment, ...], found: list[tuple[PathSegment, ...]]) -> None:
    """Report ``data``'s unknown keys under ``path``, then descend into its known ones."""
    if not isinstance(data, dict):
        return
    fields: dict[Any, Any] = {}
    payloads: dict[Any, type] = {}
    known: set[Any] = set()
    accounted = _collect(cls, data, fields, payloads, known)
    for key, value in data.items():
        field = fields.get(key)
        if field is not None:
            if value is not None:
                _descend(field, value, (*path, key), found)
        elif key in payloads:
            _walk(payloads[key], value, (*path, key), found)
        elif accounted and key not in known:
            found.append((*path, key))


def _collect(
    cls: type, data: dict[Any, Any], fields: dict[Any, Any], payloads: dict[Any, type], known: set[Any]
) -> bool:
    """Gather what one level of ``data`` may hold under ``cls``; ``False`` if some keys can't be accounted for.

    ``fields`` maps each declared wire key to its field, a flat envelope's
    selected variant included; ``payloads`` maps a nested envelope's
    ``payload_key`` to its variant; ``known`` holds the envelope keys.
    """
    accounted = True
    for _attr, wire, field in cls.__seared_fields__:  # ty: ignore[unresolved-attribute]
        if not getattr(type(field), 'UNWRAP', False):
            fields[wire] = field
            continue
        known.add(field.tag_key)
        tag = data.get(field.tag_key)
        # An unknown tag, a missing one, or one routed to the fallback: no
        # declared variant says which keys are its own.
        variant = field.variants.get(tag) if isinstance(tag, str) else None
        if field.payload_key is not None:
            known.add(field.payload_key)
            if variant is not None:
                payloads[field.payload_key] = variant
        elif variant is None:
            accounted = False
        else:
            accounted = _collect(variant, data, fields, payloads, known) and accounted
    return accounted


def _descend(field: Any, value: Any, path: tuple[PathSegment, ...], found: list[tuple[PathSegment, ...]]) -> None:
    """Walk one declared field's value, element by element for ``many`` and ``keyed``."""
    if field.keyed:
        if isinstance(value, dict):
            for key, item in value.items():
                if item is not None:
                    _one(field, item, (*path, key), found)
        return
    if field.many:
        if isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                if item is not None:
                    _one(field, item, (*path, index), found)
        return
    _one(field, value, path, found)


def _one(field: Any, value: Any, path: tuple[PathSegment, ...], found: list[tuple[PathSegment, ...]]) -> None:
    """Walk a single value: into a ``T`` target, or a ``Tuple``'s slots. Anything else has no keys of its own."""
    schema = getattr(field, 'schema', None)  # a ``T``, read as ``seared.doc`` reads it
    if schema is not None:
        _walk(schema, value, path, found)
        return
    slots = getattr(field, 'tuple_fields', None)
    if slots is not None and isinstance(value, (list, tuple)):
        for index, (slot, item) in enumerate(zip(slots, value, strict=False)):
            if item is not None:
                _descend(slot, item, (*path, index), found)


__all__ = ['unknown_keys']
