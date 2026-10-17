"""Tests for ``seared/doc/json_schema.py`` — JSON Schema 2020-12 from a class.

Two kinds of test. The tables pin what each kind and option becomes. The
corpus at the end holds the emitter to the promises it makes (plan 05 §1.4):
input valid against the load schema loads, input both refuse is refused by
both, and ``dump``'s output validates against the dump schema. Validation runs
through ``jsonschema``, a dev dependency only: seared never validates.

Its format checker asserts ``date`` and ``uuid`` here, but not ``date-time`` or
``time``, which need a package it doesn't bring; the corpus's invalid inputs
use only the formats it checks.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import decimal
import enum
from typing import TYPE_CHECKING, Any

import pytest
from jsonschema import Draft202012Validator

import seared as s
from seared import fields
from seared.doc import field_schema, json_schema
from seared.doc.json_schema import DIALECT

if TYPE_CHECKING:
    import pathlib
    import uuid


def _validator(schema: dict[str, Any]) -> Draft202012Validator:
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _one(field: Any, mode: str = 'load', annotation: Any = None) -> dict[str, Any]:
    return field_schema(field, mode=mode, defs={}, annotation=annotation)


class _Band(enum.Enum):
    UHF = 'uhf'
    HF = 'hf'


class _Level(enum.Enum):
    LOW = 1
    HIGH = 2


class TestKinds:
    @pytest.mark.parametrize(
        ('field', 'schema'),
        [
            (s.Bool(), {'type': 'boolean'}),
            (s.Int(), {'type': 'integer'}),
            (s.Float(), {'type': 'number'}),
            (s.Str(), {'type': 'string'}),
            (s.Path(), {'type': 'string'}),
            (s.UUID(), {'type': 'string', 'format': 'uuid'}),
            (s.Date(), {'type': 'string', 'format': 'date'}),
            (s.Date(format='%d/%m/%Y'), {'type': 'string'}),
            (s.TimeDelta(), {'type': 'number'}),
            (s.Decimal(), {'type': 'string'}),
            (s.Decimal(as_number=True), {'type': 'number'}),
            (s.Bytes(), {'type': 'string', 'contentEncoding': 'base64'}),
            (s.Bytes(encoding='hex'), {'type': 'string', 'contentEncoding': 'base16'}),
            (s.Enum(enum=_Band), {'type': 'string', 'enum': ['uhf', 'hf']}),
            (s.Enum(enum=_Level), {'type': 'integer', 'enum': [1, 2]}),
            (s.Dict(), {'type': 'object'}),
            (s.NDArray(), {}),
            (s.PandasFrame(), {'type': 'array', 'items': {'type': 'object'}}),
            (s.PolarsFrame(), {'type': 'array', 'items': {'type': 'object'}}),
        ],
        ids=repr,
    )
    def test_each_kind_is_the_same_in_both_modes(self, field, schema):
        assert _one(field, 'load') == schema
        assert _one(field, 'dump') == schema

    @pytest.mark.parametrize(
        ('field', 'json_format'),
        [(s.DateTime(), 'date-time'), (s.Time(), 'time')],
        ids=['DateTime', 'Time'],
    )
    def test_a_datetime_or_time_has_its_format_on_input_only(self, field, json_format):
        # A naive value's isoformat() has no offset, so it isn't RFC 3339: input
        # in that form loads, but output can't promise it.
        assert _one(field, 'load') == {'type': 'string', 'format': json_format}
        assert _one(field, 'dump') == {'type': 'string'}

    def test_a_datetime_with_its_own_format_is_a_plain_string(self):
        assert _one(s.DateTime(format='%Y%m%d %H%M'), 'load') == {'type': 'string'}

    def test_a_subclass_is_described_by_its_base(self):
        class Trimmed(s.Str):
            pass

        assert _one(Trimmed()) == {'type': 'string'}


class TestEnums:
    def test_mixed_ints_and_floats_are_numbers(self):
        class Mixed(enum.Enum):
            ONE = 1
            HALF = 0.5

        assert _one(s.Enum(enum=Mixed)) == {'type': 'number', 'enum': [1, 0.5]}

    def test_values_of_different_types_have_no_one_type(self):
        class Odd(enum.Enum):
            A = 'a'
            ONE = 1

        assert _one(s.Enum(enum=Odd)) == {'enum': ['a', 1]}

    def test_a_value_json_cant_hold_is_refused_by_name(self):
        class Pair(enum.Enum):
            ORIGIN = (0, 0)

        with pytest.raises(TypeError, match=r'Pair\.ORIGIN is \(0, 0\), which JSON has no form for'):
            _one(s.Enum(enum=Pair))


class TestWrappers:
    def test_many_is_an_array_of_elements(self):
        assert _one(s.Int(many=True)) == {'type': 'array', 'items': {'type': 'integer'}}

    def test_keyed_is_an_object_of_elements(self):
        assert _one(s.Int(keyed=True)) == {'type': 'object', 'additionalProperties': {'type': 'integer'}}

    def test_keyed_wins_over_many_as_in_load(self):
        assert _one(s.Int(keyed=True, many=True))['type'] == 'object'

    @pytest.mark.parametrize(
        ('field', 'schema'),
        [
            (s.Int(nullable=True), {'type': ['integer', 'null']}),
            (s.UUID(nullable=True), {'type': ['string', 'null'], 'format': 'uuid'}),
            (s.Enum(enum=_Band, nullable=True), {'type': ['string', 'null'], 'enum': ['uhf', 'hf', None]}),
            (s.NDArray(nullable=True), {}),
            # The container may be null; its elements may not.
            (s.Int(many=True, nullable=True), {'type': ['array', 'null'], 'items': {'type': 'integer'}}),
        ],
        ids=repr,
    )
    def test_nullable_admits_null_for_the_whole_value(self, field, schema):
        assert _one(field) == schema

    def test_a_nullable_enum_of_mixed_types_adds_null_to_its_values(self):
        class Odd(enum.Enum):
            A = 'a'
            ONE = 1

        assert _one(s.Enum(enum=Odd, nullable=True)) == {'enum': ['a', 1, None]}


class TestDict:
    @pytest.mark.parametrize(
        ('annotation', 'schema'),
        [
            (dict[str, float], {'type': 'object', 'additionalProperties': {'type': 'number'}}),
            (dict[str, int], {'type': 'object', 'additionalProperties': {'type': 'integer'}}),
            (dict[str, str] | None, {'type': 'object', 'additionalProperties': {'type': 'string'}}),
            (dict[str, list], {'type': 'object'}),
            (dict[int, str], {'type': 'object'}),
            (dict, {'type': 'object'}),
            (None, {'type': 'object'}),
        ],
        ids=repr,
    )
    def test_its_values_are_typed_from_the_annotation_when_they_can_be(self, annotation, schema):
        assert _one(s.Dict(), annotation=annotation) == schema

    def test_the_annotation_reaches_through_many(self):
        schema = _one(s.Dict(many=True), annotation=list[dict[str, bool]])
        assert schema == {'type': 'array', 'items': {'type': 'object', 'additionalProperties': {'type': 'boolean'}}}

    def test_a_class_passes_its_own_annotations(self):
        # Through the class, with string annotations, past the base's names
        # that resolve only for type checking (get_type_hints fails on them).
        @s.seared
        class Gains(s.Seared):
            gains: dict[str, float] = s.Dict(default_factory=dict)

        assert json_schema(Gains)['properties']['gains']['additionalProperties'] == {'type': 'number'}


class TestModes:
    @s.seared
    class Kinds(s.Seared):
        needed: int = s.Int(required=True)
        counted: int = s.Int(default=0)
        listed: list = s.Str(many=True, default_factory=list)
        maybe: str | None = s.Str(default=None)
        null_ok: str | None = s.Str(default=None, nullable=True)
        input_only: str | None = s.Str(default=None, dump=False)

    def test_required_on_input_is_required_true(self):
        assert json_schema(self.Kinds)['required'] == ['needed']

    def test_required_on_output_is_what_a_valid_instance_always_writes(self):
        # A value in a required field, a nullable one's None as null, and a
        # default that isn't None.
        assert json_schema(self.Kinds, mode='dump')['required'] == ['needed', 'counted', 'listed', 'null_ok']

    def test_a_field_that_isnt_dumped_is_input_only(self):
        assert 'input_only' in json_schema(self.Kinds)['properties']
        assert 'input_only' not in json_schema(self.Kinds, mode='dump')['properties']

    def test_a_data_key_names_the_property(self):
        @s.seared
        class Keyed(s.Seared):
            value: int = s.Int(data_key='v', required=True)

        schema = json_schema(Keyed)
        assert (list(schema['properties']), schema['required']) == (['v'], ['v'])

    def test_no_required_list_when_nothing_is(self):
        @s.seared
        class Loose(s.Seared):
            n: int | None = s.Int(default=None)

        assert 'required' not in json_schema(Loose)


class TestAnnotations:
    def test_doc_becomes_the_description(self):
        assert _one(s.Int(doc='metres')) == {'type': 'integer', 'description': 'metres'}

    @pytest.mark.parametrize(
        ('field', 'default'),
        [
            (s.Int(default=3), 3),
            (s.Enum(enum=_Band, default=_Band.HF), 'hf'),
            (s.Bytes(default=b'\x01\x02', encoding='hex'), '0102'),
            (s.Date(default=dt.date(2026, 10, 17)), '2026-10-17'),
            (s.Str(many=True, default=('a', 'b')), ['a', 'b']),
            (s.Decimal(default=decimal.Decimal('1.50')), '1.50'),
        ],
        ids=repr,
    )
    def test_a_static_default_shows_in_its_wire_form_on_input(self, field, default):
        assert _one(field, 'load')['default'] == default
        assert 'default' not in _one(field, 'dump')

    @pytest.mark.parametrize(
        'field',
        [s.Int(default=None), s.Str(many=True, default_factory=list), s.Int(required=True)],
        ids=repr,
    )
    def test_no_default_shows_without_one_value(self, field):
        assert 'default' not in _one(field, 'load')


class TestDocument:
    def test_a_document_declares_its_dialect_and_names_its_class(self):
        @s.seared
        class Named(s.Seared):
            """What it is.

            More about it.
            """

            n: int = s.Int(default=0)

        schema = json_schema(Named)
        assert schema['$schema'] == DIALECT == 'https://json-schema.org/draft/2020-12/schema'
        assert (schema['title'], schema['description']) == ('Named', 'What it is.\n\nMore about it.')
        assert schema['type'] == 'object'
        Draft202012Validator.check_schema(schema)

    def test_a_class_without_a_docstring_has_no_description(self):
        @s.seared
        class Bare(s.Seared):
            n: int = s.Int(default=0)

        assert 'description' not in json_schema(Bare)


class TestErrors:
    def test_a_field_with_no_kind_is_named(self):
        @dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
        class Raw(fields.Field):
            def serialize(self, value, validate=True, **kwargs):
                return value

            def deserialize(self, value, validate=True, **kwargs):
                return value

        @s.seared
        class HasRaw(s.Seared):
            odd: object = Raw(default=None)

        with pytest.raises(TypeError, match=r'^HasRaw\.odd: Raw has no field kind, so no JSON Schema; .* KIND'):
            json_schema(HasRaw)

    def test_only_a_seared_class(self):
        with pytest.raises(TypeError, match=r'json_schema\(\) takes a @seared class'):
            json_schema(dict)

    def test_only_the_two_modes(self):
        with pytest.raises(ValueError, match=r"mode= takes 'load' or 'dump', got 'read'"):
            json_schema(TestModes.Kinds, mode='read')  # ty: ignore[invalid-argument-type]
        with pytest.raises(ValueError, match='mode='):
            field_schema(s.Int(), mode='write', defs={})  # ty: ignore[invalid-argument-type]


# --- The corpus: the promises, checked with a validator -------------------------------------


@s.seared
class Everything(s.Seared):
    """One field of each kind a flat class can hold."""

    id: int = s.Int(required=True, doc='the reader')
    ratio: float = s.Float(default=1.0)
    name: str = s.Str(required=True)
    on: bool = s.Bool(default=False)
    key: uuid.UUID | None = s.UUID(default=None)
    day: dt.date | None = s.Date(default=None)
    at: dt.datetime | None = s.DateTime(default=None)
    clock: dt.time | None = s.Time(default=None)
    span: dt.timedelta | None = s.TimeDelta(default=None)
    price: decimal.Decimal | None = s.Decimal(default=None)
    blob: bytes | None = s.Bytes(default=None)
    band: _Band = s.Enum(enum=_Band, default=_Band.UHF)
    where: pathlib.Path | None = s.Path(default=None)
    gains: dict[str, float] = s.Dict(default_factory=dict)
    tags: list[str] = s.Str(many=True, default_factory=list)
    levels: dict[str, int] = s.Int(keyed=True, default_factory=dict)
    note: str | None = s.Str(default=None, nullable=True)
    secret: str | None = s.Str(default=None, dump=False)


_VALID = [
    {'id': 1, 'name': 'r1'},
    {
        'id': 2,
        'ratio': 0.5,
        'name': 'r2',
        'on': True,
        'key': '12345678-1234-5678-1234-567812345678',
        'day': '2026-10-17',
        'at': '2026-10-17T12:00:00+00:00',
        'clock': '12:30:00',
        'span': 90.5,
        'price': '19.99',
        'blob': 'AQI=',
        'band': 'hf',
        'where': 'logs/today.txt',
        'gains': {'a': 1.5},
        'tags': ['x', 'y'],
        'levels': {'low': 1},
        'note': None,
        'secret': 'shh',
    },
    {'id': 3, 'name': 'r3', 'note': 'kept'},
]

_INVALID = [
    {'name': 'no id'},
    {'id': 'x', 'name': 'r'},
    {'id': True, 'name': 'r'},
    {'id': 1.5, 'name': 'r'},
    {'id': 1, 'name': 5},
    {'id': 1, 'name': 'r', 'on': 'maybe'},
    {'id': 1, 'name': 'r', 'key': 'not-a-uuid'},
    {'id': 1, 'name': 'r', 'day': '17/10/2026'},
    {'id': 1, 'name': 'r', 'band': 'vhf'},
    {'id': 1, 'name': 'r', 'tags': ['x', 3]},
    {'id': 1, 'name': 'r', 'tags': [None]},
    {'id': 1, 'name': 'r', 'levels': {'low': 'one'}},
    {'id': 1, 'name': 'r', 'gains': []},
]


class TestThePromises:
    @pytest.mark.parametrize('data', _VALID, ids=lambda d: str(d['id']))
    def test_input_valid_against_the_load_schema_loads(self, data):
        assert _validator(json_schema(Everything)).is_valid(data)
        Everything.load(data)

    @pytest.mark.parametrize('data', _INVALID, ids=repr)
    def test_input_the_load_schema_refuses_load_refuses_too(self, data):
        assert not _validator(json_schema(Everything)).is_valid(data)
        with pytest.raises(s.ValidationError):
            Everything.load(data)

    @pytest.mark.parametrize('data', _VALID, ids=lambda d: str(d['id']))
    def test_what_dump_writes_validates_against_the_dump_schema(self, data):
        dumped = Everything.dump(Everything.load(data))
        _validator(json_schema(Everything, mode='dump')).validate(dumped)

    def test_the_dump_schema_requires_what_dump_always_writes(self):
        dumped = Everything.dump(Everything.load(_VALID[0]))
        schema = json_schema(Everything, mode='dump')
        assert set(schema['required']) <= set(dumped)
        assert not _validator(schema).is_valid({k: v for k, v in dumped.items() if k != 'note'})
