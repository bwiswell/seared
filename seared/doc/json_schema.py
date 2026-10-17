"""JSON Schema 2020-12 from a ``@seared`` class (0.4.2).

:func:`json_schema` describes a class's JSON wire form, in one of two modes:

- ``mode='load'``, the canonical input: the form a producer should send. An
  instance valid against it, honouring its ``format`` and ``contentEncoding``
  annotations, loads. ``load`` accepts more than this (numeric strings, ``'yes'``
  for a bool, ``null`` on an optional field), and the schema leaves that out.
- ``mode='dump'``, the output: what ``dump`` writes for a valid instance, one
  ``load`` built or one constructed with valid values. ``dump``'s output
  validates against it.

:func:`field_schema` is the unit both are built from: one field's schema, for a
caller composing an object of its own.

It describes the JSON carrier. Under msgpack a ``Bytes`` field travels as raw
bytes, which no schema here describes. And it only describes: seared validates
by loading, so nothing here validates against a schema.
"""

from __future__ import annotations

import annotationlib
import types
import typing
from typing import Any, Literal, get_args, get_origin

from seared._core.errors import ValidationError
from seared.fields.kind import FieldKind, field_kind

from .introspect import introspect, is_seared_class

#: The dialect every document declares.
DIALECT = 'https://json-schema.org/draft/2020-12/schema'

type Mode = Literal['load', 'dump']

#: A Python value's JSON Schema type, for the values an ``Enum`` or a refined
#: ``Dict`` can hold. ``bool`` before ``int``: a bool is an int to ``isinstance``.
_JSON_TYPES: tuple[tuple[type, str], ...] = (
    (bool, 'boolean'),
    (int, 'integer'),
    (float, 'number'),
    (str, 'string'),
    (type(None), 'null'),
)


def json_schema(cls: type, *, mode: Mode = 'load') -> dict[str, Any]:
    """The JSON Schema of ``cls``'s wire form, as a whole document.

    Args:
        cls: A ``@seared`` class.
        mode: ``'load'`` for the canonical input, ``'dump'`` for what ``dump``
            writes (see the module docstring for what each promises).

    Returns:
        A JSON Schema 2020-12 document: ``$schema``, ``title`` (the class
        name), ``description`` (its docstring, when it has one), and the
        object schema.

    Raises:
        TypeError: If ``cls`` isn't a ``@seared`` class, or a field has no JSON
            Schema (a field class with no kind, or an enum value JSON can't
            hold); the message names the field.
        ValueError: If ``mode`` is neither ``'load'`` nor ``'dump'``.
    """
    _check_mode(mode)
    if not is_seared_class(cls):
        msg = f'json_schema() takes a @seared class, got {cls!r}'
        raise TypeError(msg)
    defs: dict[str, Any] = {}
    out: dict[str, Any] = {'$schema': DIALECT, 'title': cls.__name__}
    doc = introspect(cls).doc
    if doc:
        out['description'] = doc
    out.update(_object_schema(cls, mode, defs))
    if defs:
        out['$defs'] = dict(sorted(defs.items()))
    return out


def field_schema(
    field: Any,
    *,
    mode: Mode = 'load',
    defs: dict[str, Any],
    annotation: Any = None,
) -> dict[str, Any]:
    """The JSON Schema of one field's value.

    Args:
        field: A field, such as one from ``Cls.__seared_fields__``.
        mode: ``'load'`` or ``'dump'``, as for :func:`json_schema`.
        defs: Where the schemas of the classes the field refers to go, keyed by
            name, for the caller to place under ``$defs``.
        annotation: The field's annotation, which refines a ``Dict``'s values
            (``dict[str, int]``); optional.

    Returns:
        The field's schema, its ``doc=`` as ``description`` and, in load mode,
        its static default as ``default``.

    Raises:
        TypeError: If the field has no JSON Schema.
        ValueError: If ``mode`` is neither ``'load'`` nor ``'dump'``.
    """
    _check_mode(mode)
    schema = _kind_schema(field, mode, defs, _element_annotation(field, annotation))
    # ``keyed`` before ``many``, as ``load`` applies them. Elements are never null.
    if field.keyed:
        schema = {'type': 'object', 'additionalProperties': schema}
    elif field.many:
        schema = {'type': 'array', 'items': schema}
    if field.nullable:
        schema = _or_null(schema)
    if field.doc:
        schema['description'] = field.doc
    if mode == 'load':
        default = _wire_default(field)
        if default is not _NO_DEFAULT:
            schema['default'] = default
    return schema


def _check_mode(mode: object) -> None:
    if mode not in ('load', 'dump'):
        msg = f"mode= takes 'load' or 'dump', got {mode!r}"
        raise ValueError(msg)


def _object_schema(cls: Any, mode: Mode, defs: dict[str, Any]) -> dict[str, Any]:
    """A class's object schema: its properties by wire key, and which are required."""
    hints = _hints(cls)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for attr, wire, f in cls.__seared_fields__:
        if mode == 'dump' and not f.dump:
            continue
        try:
            properties[wire] = field_schema(f, mode=mode, defs=defs, annotation=hints.get(attr))
        except TypeError as exc:
            msg = f'{cls.__name__}.{attr}: {exc}'
            raise TypeError(msg) from None
        if _always_present(f, mode):
            required.append(wire)
    schema: dict[str, Any] = {'type': 'object', 'properties': properties}
    if required:
        schema['required'] = required
    return schema


def _always_present(f: Any, mode: Mode) -> bool:
    """Whether the field's key is required: on input, ``required=True``; in a dump, whenever a valid instance writes it.

    A valid instance holds a value in a required field, writes a nullable one's
    ``None`` as ``null``, and holds its default, which ``dump`` writes, unless
    that default is ``None``.
    """
    if mode == 'load':
        return bool(f.required)
    return bool(f.required or f.nullable or f.default_factory is not None or f.default is not None)


def _kind_schema(field: Any, mode: Mode, defs: dict[str, Any], annotation: Any) -> dict[str, Any]:
    """The schema of one element of the field, by its kind."""
    kind = field_kind(field)
    if kind is None:
        msg = (
            f'{type(field).__name__} has no field kind, so no JSON Schema; '
            'a field class names one with KIND (see seared.fields.kind)'
        )
        raise TypeError(msg)
    build = _BUILDERS.get(kind)
    if build is None:
        msg = f'no JSON Schema for a {kind} field'
        raise TypeError(msg)
    return build(field, mode, defs, annotation)


def _scalar(json_type: str, **extra: Any) -> Any:
    def build(_field: Any, _mode: Mode, _defs: dict[str, Any], _annotation: Any) -> dict[str, Any]:
        return {'type': json_type, **extra}

    return build


def _temporal(json_format: str, *, load_only: bool) -> Any:
    """A date, datetime or time: an ISO string, with its ``format`` when it's an exact one.

    Only ``date`` is exact both ways. A naive ``datetime`` or ``time``'s
    ``isoformat()`` has no offset, so it isn't RFC 3339's ``date-time`` or
    ``time``: input in that form loads, but output can't promise it.
    """

    def build(field: Any, mode: Mode, _defs: dict[str, Any], _annotation: Any) -> dict[str, Any]:
        if field.format is not None or (load_only and mode == 'dump'):
            return {'type': 'string'}
        return {'type': 'string', 'format': json_format}

    return build


def _decimal(field: Any, _mode: Mode, _defs: dict[str, Any], _annotation: Any) -> dict[str, Any]:
    return {'type': 'number'} if field.as_number else {'type': 'string'}


def _bytes(field: Any, _mode: Mode, _defs: dict[str, Any], _annotation: Any) -> dict[str, Any]:
    return {'type': 'string', 'contentEncoding': 'base16' if field.encoding == 'hex' else 'base64'}


def _enum(field: Any, _mode: Mode, _defs: dict[str, Any], _annotation: Any) -> dict[str, Any]:
    values = []
    kinds = set()
    for member in field.enum:
        json_type = _json_type(member.value)
        if json_type is None:
            msg = f'{field.enum.__name__}.{member.name} is {member.value!r}, which JSON has no form for'
            raise TypeError(msg)
        values.append(member.value)
        kinds.add(json_type)
    if kinds <= {'integer', 'number'} and len(kinds) == 2:  # noqa: PLR2004
        kinds = {'number'}
    if len(kinds) == 1:
        return {'type': kinds.pop(), 'enum': values}
    return {'enum': values}


def _dict(_field: Any, _mode: Mode, _defs: dict[str, Any], annotation: Any) -> dict[str, Any]:
    """An object; its values typed when the annotation is ``dict[str, X]`` for a JSON scalar ``X``.

    seared passes a ``Dict``'s values through unchecked, so the annotation is
    the only word on them. Anything else stays an untyped object.
    """
    schema: dict[str, Any] = {'type': 'object'}
    if get_origin(annotation) is dict:
        args = get_args(annotation)
        if len(args) == 2 and args[0] is str:  # noqa: PLR2004
            value_type = dict(_JSON_TYPES).get(args[1])
            if value_type is not None and value_type != 'null':
                schema['additionalProperties'] = {'type': value_type}
    return schema


def _opaque(_field: Any, _mode: Mode, _defs: dict[str, Any], _annotation: Any) -> dict[str, Any]:
    """An array: its nested lists hold any shape, and a 0-d one dumps as a scalar."""
    return {}


def _records(_field: Any, _mode: Mode, _defs: dict[str, Any], _annotation: Any) -> dict[str, Any]:
    """A frame: the list of row records both frame fields write and a strict load requires."""
    return {'type': 'array', 'items': {'type': 'object'}}


_BUILDERS: dict[FieldKind, Any] = {
    FieldKind.BOOL: _scalar('boolean'),
    FieldKind.INT: _scalar('integer'),
    FieldKind.FLOAT: _scalar('number'),
    FieldKind.STR: _scalar('string'),
    FieldKind.PATH: _scalar('string'),
    FieldKind.UUID: _scalar('string', format='uuid'),
    FieldKind.DATE: _temporal('date', load_only=False),
    FieldKind.DATETIME: _temporal('date-time', load_only=True),
    FieldKind.TIME: _temporal('time', load_only=True),
    FieldKind.TIMEDELTA: _scalar('number'),
    FieldKind.DECIMAL: _decimal,
    FieldKind.BYTES: _bytes,
    FieldKind.ENUM: _enum,
    FieldKind.DICT: _dict,
    FieldKind.NDARRAY: _opaque,
    FieldKind.PANDAS: _records,
    FieldKind.POLARS: _records,
}


def _json_type(value: object) -> str | None:
    for py_type, json_type in _JSON_TYPES:
        if isinstance(value, py_type):
            return json_type
    return None


def _or_null(schema: dict[str, Any]) -> dict[str, Any]:
    """``schema``, admitting ``null`` as well."""
    if not schema:
        return schema  # ``{}`` admits it already
    json_type = schema.get('type')
    if 'enum' in schema:
        schema = {**schema, 'enum': [*schema['enum'], None]}
    if isinstance(json_type, str):
        return {**schema, 'type': [json_type, 'null']}
    if 'enum' in schema:
        return schema
    return {'anyOf': [schema, {'type': 'null'}]}


def _element_annotation(field: Any, annotation: Any) -> Any:
    """The annotation of one element: ``X`` out of ``list[X]``, ``dict[str, X]`` or ``X | None``."""
    annotation = _strip_none(annotation)
    container = dict if field.keyed else list if field.many else None
    if container is None:
        return annotation
    args = get_args(annotation) if get_origin(annotation) is container else ()
    return _strip_none(args[-1]) if args else None


def _strip_none(annotation: Any) -> Any:
    if get_origin(annotation) in (typing.Union, types.UnionType):
        rest = [a for a in get_args(annotation) if a is not type(None)]
        return rest[0] if len(rest) == 1 else None
    return annotation


def _hints(cls: type) -> dict[str, Any]:
    """The class's field annotations, each resolved on its own; one that won't resolve is left out.

    ``get_type_hints`` resolves a class's whole hierarchy or nothing, and the
    ``Seared`` base names types imported only for type checking, so it fails
    for every ``@seared`` class. Annotations only refine a schema, so each is
    taken where it resolves.
    """
    hints: dict[str, Any] = {}
    for klass in reversed(cls.__mro__):
        try:
            annotations = annotationlib.get_annotations(klass, format=annotationlib.Format.FORWARDREF)
        except Exception:  # noqa: BLE001, S112 — best-effort, as above
            continue
        for name, annotation in annotations.items():
            resolved = _resolve(annotation, klass)
            if resolved is not _UNRESOLVED:
                hints[name] = resolved
    return hints


_UNRESOLVED = object()


def _resolve(annotation: Any, klass: type) -> Any:
    """An annotation as a value: a string or a forward reference evaluated in ``klass``'s module."""
    if isinstance(annotation, str):
        annotation = annotationlib.ForwardRef(annotation, module=klass.__module__, is_class=True)
    if not isinstance(annotation, annotationlib.ForwardRef):
        return annotation
    try:
        return annotation.evaluate(owner=klass)
    except Exception:  # noqa: BLE001 — best-effort, as above
        return _UNRESOLVED


class _NoDefault:
    pass


_NO_DEFAULT = _NoDefault()


def _wire_default(field: Any) -> Any:
    """The field's static default in its wire form, or ``_NO_DEFAULT``.

    A ``default_factory`` is called per instance, so it has no one value to
    show, and a ``None`` default reads as an absent key. A default the field
    can't serialize isn't shown.
    """
    if field.default_factory is not None or field.default is None:
        return _NO_DEFAULT
    value = field.default
    try:
        if field.keyed:
            wire = {key: field.serialize(item) for key, item in value.items()}
        elif field.many:
            wire = [field.serialize(item) for item in value]
        else:
            wire = field.serialize(value)
    except ValidationError, TypeError, AttributeError:
        return _NO_DEFAULT
    return _jsonable(wire)


def _jsonable(value: Any) -> Any:
    """``value`` with its tuples as lists, the form JSON gives them."""
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


__all__ = ['DIALECT', 'Mode', 'field_schema', 'json_schema']
