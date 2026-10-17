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
import json
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


def _written(cls: Any, data: dict[str, Any]) -> Any:
    """What ``dumps`` writes for ``data``'s instance, read back: the JSON carrier the dump schema describes.

    ``dump`` alone hands back a ``Tuple`` as a Python tuple, which JSON writes as an array.
    """
    return json.loads(cls.dumps(cls.load(data)))


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
        _validator(json_schema(Everything, mode='dump')).validate(_written(Everything, data))

    def test_the_dump_schema_requires_what_dump_always_writes(self):
        dumped = _written(Everything, _VALID[0])
        schema = json_schema(Everything, mode='dump')
        assert set(schema['required']) <= set(dumped)
        assert not _validator(schema).is_valid({k: v for k, v in dumped.items() if k != 'note'})


# --- Nested classes, tuples, unions and closedness (plan 05 §1.6, §1.7) ----------------------


@s.seared
class Point(s.Seared):
    """A point on the floor."""

    x: float = s.Float(required=True)
    y: float = s.Float(required=True)


@s.seared
class Start(s.Seared):
    speed: int = s.Int(required=True)


@s.seared
class Stop(s.Seared):
    reason: str | None = s.Str(default=None)


@s.seared
class Other(s.Seared):
    pass


@s.seared
class Command(s.Seared):
    """A flat union, nested classes and a tuple."""

    id: int = s.Int(required=True)
    at: Point = s.T(Point, required=True)
    path: list[Point] = s.T(Point, many=True, default_factory=list)
    pair: tuple = s.Tuple(s.Int(), s.Str(doc='its label'), default=(0, ''))
    action: object = s.Union(variants={'start': Start, 'stop': Stop}, doc='what to do')


@s.seared
class Envelope(s.Seared):
    """A nested union with a fallback."""

    id: int = s.Int(required=True)
    task: object = s.Union(variants={'start': Start, 'stop': Stop}, tag_key='kind', payload_key='args', fallback=Other)


class TestNested:
    def test_a_nested_class_is_a_reference_to_its_definition(self):
        schema = json_schema(Command)
        assert schema['properties']['at'] == {'$ref': '#/$defs/Point'}
        assert schema['$defs']['Point'] == {
            'title': 'Point',
            'description': 'A point on the floor.',
            'type': 'object',
            'properties': {'x': {'type': 'number'}, 'y': {'type': 'number'}},
            'required': ['x', 'y'],
        }

    def test_a_class_used_twice_is_defined_once(self):
        schema = json_schema(Command)
        assert schema['properties']['path'] == {'type': 'array', 'items': {'$ref': '#/$defs/Point'}}
        assert sorted(schema['$defs']) == ['Point', 'Start', 'Stop']

    def test_a_nullable_nested_class_is_a_reference_or_null(self):
        @s.seared
        class Maybe(s.Seared):
            at: Point | None = s.T(Point, default=None, nullable=True)

        assert json_schema(Maybe)['properties']['at'] == {'anyOf': [{'$ref': '#/$defs/Point'}, {'type': 'null'}]}

    def test_two_classes_of_one_name_get_two_definitions(self):
        def make(field_name):
            @s.seared
            class Inner(s.Seared):
                n: int = s.Int(default=0, data_key=field_name)

            return Inner

        first, second = make('a'), make('b')

        @s.seared
        class Both(s.Seared):
            one: object = s.T(first, required=True)
            two: object = s.T(second, required=True)

        schema = json_schema(Both)
        refs = [schema['properties'][key]['$ref'] for key in ('one', 'two')]
        assert refs == ['#/$defs/Inner', f'#/$defs/{__name__}.Inner']
        validator = _validator(schema)
        assert validator.is_valid({'one': {'a': 1}, 'two': {'b': 2}})
        assert not validator.is_valid({'one': {'a': 1}, 'two': {'b': 'x'}})

    def test_field_schema_fills_the_callers_defs_and_shares_them(self):
        defs: dict[str, Any] = {}
        assert field_schema(s.T(Point), defs=defs) == {'$ref': '#/$defs/Point'}
        assert field_schema(s.T(Point, many=True), defs=defs) == {'type': 'array', 'items': {'$ref': '#/$defs/Point'}}
        assert list(defs) == ['Point']


class TestTuple:
    def test_a_tuple_is_a_fixed_length_array_one_schema_per_slot(self):
        assert json_schema(Command)['properties']['pair'] == {
            'type': 'array',
            'prefixItems': [{'type': 'integer'}, {'type': 'string', 'description': 'its label'}],
            'items': False,
            'minItems': 2,
            'maxItems': 2,
            'default': [0, ''],
        }

    def test_a_slots_own_options_dont_apply(self):
        # Tuple hands each value to its slot field directly.
        assert _one(s.Tuple(s.Int(many=True, nullable=True)))['prefixItems'] == [{'type': 'integer'}]


class TestUnion:
    def test_a_flat_union_is_an_envelope_beside_the_parents_keys(self):
        schema = json_schema(Command)
        assert 'action' not in schema['properties']
        assert schema['allOf'] == [
            {
                'type': 'object',
                'properties': {'type': {'type': 'string', 'enum': ['start', 'stop']}},
                'required': ['type'],
                'allOf': [
                    {
                        'if': {'properties': {'type': {'const': 'start'}}, 'required': ['type']},
                        'then': {'$ref': '#/$defs/Start'},
                    },
                    {
                        'if': {'properties': {'type': {'const': 'stop'}}, 'required': ['type']},
                        'then': {'$ref': '#/$defs/Stop'},
                    },
                ],
                'description': 'what to do',
            }
        ]

    def test_a_nested_payload_is_required_only_where_an_empty_one_wont_load(self):
        branches = json_schema(Envelope)['allOf'][0]['allOf']
        start, stop = branches[0]['then'], branches[1]['then']
        assert start == {'properties': {'args': {'$ref': '#/$defs/Start'}}, 'required': ['args']}
        assert stop == {'properties': {'args': {'$ref': '#/$defs/Stop'}}}

    def test_a_dump_always_writes_the_payload(self):
        branches = json_schema(Envelope, mode='dump')['allOf'][0]['allOf']
        assert all(branch['then']['required'] == ['args'] for branch in branches)

    def test_a_fallback_takes_any_other_tag_on_input(self):
        envelope = json_schema(Envelope)['allOf'][0]
        assert envelope['properties']['kind'] == {'type': 'string'}
        assert envelope['allOf'][-1] == {
            'if': {'properties': {'kind': {'enum': ['start', 'stop']}}},
            'else': {'properties': {'args': {'$ref': '#/$defs/Other'}}},
        }

    def test_a_dump_writes_only_the_declared_tags(self):
        envelope = json_schema(Envelope, mode='dump')['allOf'][0]
        assert envelope['properties']['kind'] == {'type': 'string', 'enum': ['start', 'stop']}
        assert len(envelope['allOf']) == 2


class TestClosed:
    def test_a_refusing_class_is_closed_by_default(self):
        @s.seared(unknown='raise')
        class Strict(s.Seared):
            at: Point = s.T(Point, required=True)

        schema = json_schema(Strict)
        assert schema['unevaluatedProperties'] is False
        assert schema['properties']['at'] == {'$ref': '#/$defs/Point', 'unevaluatedProperties': False}
        assert 'unevaluatedProperties' not in json_schema(Strict, unknown='ignore')

    def test_closing_reaches_every_object_but_not_a_definition(self):
        schema = json_schema(Command, unknown='raise')
        assert schema['unevaluatedProperties'] is False
        assert schema['properties']['path']['items'] == {'$ref': '#/$defs/Point', 'unevaluatedProperties': False}
        # A flat variant shares its parent's object, which is closed already.
        assert schema['allOf'][0]['allOf'][0]['then'] == {'$ref': '#/$defs/Start'}
        assert all('unevaluatedProperties' not in d for d in schema['$defs'].values())

    def test_a_fallback_payload_stays_open(self):
        envelope = json_schema(Envelope, unknown='raise')['allOf'][0]
        assert envelope['allOf'][0]['then']['properties']['args']['unevaluatedProperties'] is False
        assert envelope['allOf'][-1]['else'] == {'properties': {'args': {'$ref': '#/$defs/Other'}}}

    def test_a_flat_fallback_marks_its_keys_as_evaluated(self):
        @s.seared
        class Flat(s.Seared):
            task: object = s.Union(variants={'start': Start}, fallback=Other)

        envelope = json_schema(Flat, unknown='raise')['allOf'][0]
        assert envelope['allOf'][-1]['else'] == {'$ref': '#/$defs/Other', 'unevaluatedProperties': True}

    def test_only_the_two_values(self):
        with pytest.raises(ValueError, match=r"json_schema\(\): unknown= takes 'ignore' or 'raise', got 'deny'"):
            json_schema(Command, unknown='deny')  # ty: ignore[invalid-argument-type]


_NESTED_VALID = [
    (Command, {'id': 1, 'at': {'x': 0, 'y': 1}, 'type': 'start', 'speed': 3}),
    (Command, {'id': 2, 'at': {'x': 0, 'y': 1}, 'path': [{'x': 1, 'y': 1}], 'pair': [5, 'five'], 'type': 'stop'}),
    (Envelope, {'id': 1, 'kind': 'start', 'args': {'speed': 2}}),
    (Envelope, {'id': 2, 'kind': 'stop'}),
    (Envelope, {'id': 3, 'kind': 'jump', 'args': {'height': 9}}),
]

_NESTED_INVALID = [
    (Command, {'id': 1, 'type': 'start', 'speed': 3}),
    (Command, {'id': 1, 'at': {'x': 0}, 'type': 'start', 'speed': 3}),
    (Command, {'id': 1, 'at': {'x': 0, 'y': 1}, 'type': 'start'}),
    (Command, {'id': 1, 'at': {'x': 0, 'y': 1}, 'type': 'jump'}),
    (Command, {'id': 1, 'at': {'x': 0, 'y': 1}}),
    (Command, {'id': 1, 'at': {'x': 0, 'y': 1}, 'type': 'stop', 'pair': [1]}),
    (Command, {'id': 1, 'at': {'x': 0, 'y': 1}, 'type': 'stop', 'pair': ['one', 'a']}),
    (Command, {'id': 1, 'at': {'x': 0, 'y': 1}, 'type': 'stop', 'path': [{'x': 'a', 'y': 1}]}),
    (Envelope, {'id': 1, 'kind': 'start'}),
    (Envelope, {'id': 1, 'kind': 'start', 'args': {'speed': 'fast'}}),
    (Envelope, {'id': 1}),
]

#: Otherwise valid inputs, some carrying keys no class declares.
_CLOSED = [
    (Command, {'id': 1, 'at': {'x': 0, 'y': 1}, 'type': 'start', 'speed': 3}),
    (Command, {'id': 1, 'at': {'x': 0, 'y': 1}, 'type': 'start', 'speed': 3, 'extra': 1}),
    (Command, {'id': 1, 'at': {'x': 0, 'y': 1, 'z': 2}, 'type': 'start', 'speed': 3}),
    (Command, {'id': 1, 'at': {'x': 0, 'y': 1}, 'path': [{'x': 1, 'y': 1}, {'x': 1, 'y': 1, 'w': 0}], 'type': 'stop'}),
    # A key that only the other variant declares.
    (Command, {'id': 1, 'at': {'x': 0, 'y': 1}, 'type': 'start', 'speed': 3, 'reason': 'x'}),
    (Envelope, {'id': 1, 'kind': 'start', 'args': {'speed': 2}}),
    (Envelope, {'id': 1, 'kind': 'start', 'args': {'speed': 2, 'sped': 3}}),
    (Envelope, {'id': 1, 'kind': 'stop', 'extra': True}),
    # A fallback payload is never checked.
    (Envelope, {'id': 1, 'kind': 'jump', 'args': {'height': 9}}),
    (Envelope, {'id': 1, 'kind': 'jump', 'args': {'height': 9}, 'extra': True}),
]


def _case_id(case):
    return f'{case[0].__name__}:{case[1]}'


class TestThePromisesNested:
    @pytest.mark.parametrize('case', _NESTED_VALID, ids=_case_id)
    def test_input_valid_against_the_load_schema_loads(self, case):
        cls, data = case
        assert _validator(json_schema(cls)).is_valid(data)
        cls.load(data)

    @pytest.mark.parametrize('case', _NESTED_INVALID, ids=_case_id)
    def test_input_the_load_schema_refuses_load_refuses_too(self, case):
        cls, data = case
        assert not _validator(json_schema(cls)).is_valid(data)
        with pytest.raises(s.ValidationError):
            cls.load(data)

    @pytest.mark.parametrize('case', [c for c in _NESTED_VALID if c[1]['id'] != 3 or c[0] is Command], ids=_case_id)
    def test_what_dump_writes_validates_against_the_dump_schema(self, case):
        # Not the fallback case: ``dump`` writes only a declared variant.
        cls, data = case
        _validator(json_schema(cls, mode='dump')).validate(_written(cls, data))

    @pytest.mark.parametrize('case', _CLOSED, ids=_case_id)
    def test_a_closed_schema_refuses_exactly_what_unknown_keys_reports(self, case):
        cls, data = case
        refused = not _validator(json_schema(cls, unknown='raise')).is_valid(data)
        assert refused == bool(s.unknown_keys(cls, data))
        assert _validator(json_schema(cls, unknown='ignore')).is_valid(data)
