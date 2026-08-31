"""Runtime introspection of ``@seared`` classes into a structured model.

``introspect(cls)`` walks ``cls.__seared_fields__`` plus the resolved
annotations and returns a :class:`SchemaDoc` tree — the stable, render-agnostic
intermediate that ``seared.doc.render`` (and zeared's wire-aware renderer, and
any future JSON-Schema / HTML output) consume. Pure stdlib.
"""
from __future__ import annotations

import enum as _enum
import inspect
import re
from dataclasses import dataclass, field as _dc_field
from typing import Any, Optional, TypeGuard, get_args, get_origin, get_type_hints

from .._core.base import Seared


@dataclass(frozen=True, slots=True)
class EnumDoc:
    name: str
    members: tuple[tuple[str, Any], ...]  # (member name, wire value)


@dataclass(frozen=True, slots=True)
class VariantDoc:
    tag: str
    cls: type


@dataclass(frozen=True, slots=True)
class FieldDoc:
    attr: str
    wire_key: Optional[str]        # None when identical to ``attr``
    type_str: str
    required: bool
    default_repr: str
    many: bool
    keyed: bool
    dump: bool
    doc: Optional[str]
    enum: Optional[EnumDoc] = None
    nested: Optional[type] = None                 # T(schema) target
    variants: Optional[tuple[VariantDoc, ...]] = None
    envelope: Optional[str] = None                # Union envelope description
    fallback: Optional[type] = None               # Union default variant


@dataclass(frozen=True, slots=True)
class SchemaDoc:
    cls: type
    name: str
    module: str
    doc: Optional[str]
    summary: Optional[str]
    fields: tuple[FieldDoc, ...]
    is_message: bool = False
    # Classes this schema references (T targets, Union variants) — the
    # transitive set the generator should also document + cross-link.
    references: tuple[type, ...] = _dc_field(default=())


def is_seared_class(obj: Any) -> TypeGuard[type[Seared]]:
    """True for a decorated ``@seared`` class (not the base itself)."""
    return (
        isinstance(obj, type)
        and issubclass(obj, Seared)
        and obj is not Seared
        and bool(getattr(obj, '__seared_fields__', ()))
    )


def introspect(cls: type[Seared]) -> SchemaDoc:
    """Introspect a ``@seared`` class into a :class:`SchemaDoc`."""
    type_strings = _type_strings(cls)
    fields: list[FieldDoc] = []
    references: list[type] = []
    for attr, wire, f in cls.__seared_fields__:
        fd = _field_doc(attr, wire, f, type_strings.get(attr, '?'))
        fields.append(fd)
        if fd.nested is not None:
            references.append(fd.nested)
        if fd.variants:
            references.extend(v.cls for v in fd.variants)
        if fd.fallback is not None:
            references.append(fd.fallback)
    doc = _clean_doc(inspect.cleandoc(cls.__doc__)) if cls.__doc__ else None
    summary = doc.splitlines()[0] if doc else None
    # Dedupe references preserving order.
    seen: set[int] = set()
    refs = tuple(r for r in references if not (id(r) in seen or seen.add(id(r))))
    return SchemaDoc(
        cls=cls,
        name=cls.__name__,
        module=cls.__module__,
        doc=doc,
        summary=summary,
        fields=tuple(fields),
        references=refs,
    )


_RST_ROLE = re.compile(r':[\w.]+:(`[^`]+`)')


def _clean_doc(text: str) -> str:
    """Strip RST role prefixes so Sphinx-flavoured docstrings read as Markdown.

    ``:class:`HttpRequest``` → ```HttpRequest```. Double-backtick literals
    (```` ``x`` ````) are left as-is — they already render as Markdown code.
    """
    return _RST_ROLE.sub(r'\1', text)


def _field_doc(attr: str, wire: str, f: Any, type_str: str) -> FieldDoc:
    enum = nested = variants = envelope = fallback = None
    if hasattr(f, 'enum') and getattr(f, 'enum', None) is not None:
        e = f.enum
        enum = EnumDoc(name=e.__name__, members=tuple((m.name, m.value) for m in e))
    elif hasattr(f, 'variants'):
        variants = tuple(VariantDoc(tag=t, cls=c) for t, c in f.variants.items())
        envelope = (
            'flat' if getattr(f, 'payload_key', None) is None
            else f'nested under `{f.payload_key}`'
        )
        fallback = getattr(f, 'default', None)
    elif hasattr(f, 'schema'):
        nested = f.schema
    return FieldDoc(
        attr=attr,
        wire_key=None if wire == attr else wire,
        type_str=type_str,
        required=bool(f.required),
        default_repr=_default_repr(f),
        many=bool(f.many),
        keyed=bool(f.keyed),
        dump=bool(f.dump),
        doc=getattr(f, 'doc', None),
        enum=enum,
        nested=nested,
        variants=variants,
        envelope=envelope,
        fallback=fallback,
    )


def _default_repr(f: Any) -> str:
    if f.required:
        return '—'
    factory = getattr(f, 'default_factory', None)
    if factory is not None:
        return f'`<factory: {getattr(factory, "__name__", "callable")}>`'
    value = f.missing  # resolved default (default= folds into missing)
    if value is None:
        return '`null`'
    if isinstance(value, _enum.Enum):
        return f'`{type(value).__name__}.{value.name}`'
    return f'`{value!r}`'


def _type_strings(cls: type) -> dict[str, str]:
    """attr -> display type string, resolving stringized annotations.

    Falls back to raw annotation strings walked up the MRO when
    ``get_type_hints`` can't resolve a forward ref (degrade, never fail).
    """
    try:
        hints = get_type_hints(cls)
        return {k: _format_type(v) for k, v in hints.items()}
    except Exception:  # noqa: BLE001 — resolution is best-effort
        out: dict[str, str] = {}
        for klass in reversed(cls.__mro__):
            for k, v in getattr(klass, '__annotations__', {}).items():
                out[k] = v if isinstance(v, str) else _format_type(v)
        return out


def _format_type(tp: Any) -> str:
    if tp is type(None):
        return 'None'
    if isinstance(tp, str):
        return tp
    origin = get_origin(tp)
    if origin is not None:
        args = get_args(tp)
        # Union / Optional (both typing.Union and X | Y): join, None last.
        if _is_union(tp):
            parts = [_format_type(a) for a in args if a is not type(None)]
            if any(a is type(None) for a in args):
                parts.append('None')
            return ' | '.join(parts)
        name = getattr(origin, '__name__', None) or str(origin).replace('typing.', '')
        if args:
            return f'{name}[{", ".join(_format_type(a) for a in args)}]'
        return name
    return getattr(tp, '__name__', None) or str(tp).replace('typing.', '')


def _is_union(tp: Any) -> bool:
    import types as _types
    import typing as _typing
    return get_origin(tp) is _typing.Union or isinstance(tp, _types.UnionType)
