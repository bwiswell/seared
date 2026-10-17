"""Tests for ``seared/fields/kind.py`` — a field's kind, through the class hierarchy.

The point of a public kind is that a subclass keeps its base's, where a table
keyed on ``type(field).__name__`` lost it. The accelerator keeps its exact-class
gate (``tests/_core/test_accel.py``), so the two rules are pinned apart.
"""

from __future__ import annotations

import dataclasses
import enum

import pytest

import seared as s
from seared import fields
from seared.fields.kind import FieldKind, field_kind


class _Color(enum.Enum):
    RED = 'r'


@s.seared
class _Inner(s.Seared):
    n: int = s.Int(default=0)


#: One field of each built-in class, and the kind it should report.
_BUILT_IN = [
    (s.Int(), FieldKind.INT),
    (s.Float(), FieldKind.FLOAT),
    (s.Str(), FieldKind.STR),
    (s.Bool(), FieldKind.BOOL),
    (s.T(_Inner), FieldKind.NESTED),
    (s.UUID(), FieldKind.UUID),
    (s.Date(), FieldKind.DATE),
    (s.DateTime(), FieldKind.DATETIME),
    (s.Time(), FieldKind.TIME),
    (s.TimeDelta(), FieldKind.TIMEDELTA),
    (s.Decimal(), FieldKind.DECIMAL),
    (s.Bytes(), FieldKind.BYTES),
    (s.Enum(enum=_Color), FieldKind.ENUM),
    (s.Path(), FieldKind.PATH),
    (s.Dict(), FieldKind.DICT),
    (s.Tuple(s.Int(), s.Str()), FieldKind.TUPLE),
    (s.Union(variants={'inner': _Inner}), FieldKind.UNION),
    (s.NDArray(), FieldKind.NDARRAY),
    (s.PandasFrame(), FieldKind.PANDAS),
    (s.PolarsFrame(), FieldKind.POLARS),
]


@pytest.mark.parametrize(('field', 'kind'), _BUILT_IN, ids=[type(f).__name__ for f, _ in _BUILT_IN])
def test_each_built_in_field_has_its_own_kind(field, kind):
    assert field_kind(field) is kind
    assert field_kind(type(field)) is kind  # the class answers too


def test_every_kind_belongs_to_exactly_one_built_in_class():
    assert sorted(kind for _, kind in _BUILT_IN) == sorted(FieldKind)


def test_kinds_are_their_names_as_strings():
    # A StrEnum: a consumer's table can key on the plain name too.
    assert FieldKind.NESTED == 'nested'
    assert str(FieldKind.DATETIME) == 'datetime'


class TestSubclasses:
    def test_a_subclass_keeps_its_bases_kind(self):
        # The case the kind exists for: rio's secret-reference field subclasses
        # ``Str`` to check its value, and keeps ``Str``'s wire form.
        class Checked(s.Str):
            def deserialize(self, value, validate=True, **kwargs):
                return super().deserialize(value, validate, **kwargs).strip()

        class CheckedTwice(Checked):
            pass

        assert field_kind(Checked()) is FieldKind.STR
        assert field_kind(CheckedTwice()) is FieldKind.STR

    def test_a_subclass_that_changes_the_wire_form_names_its_own(self):
        class Seconds(s.Float):
            KIND = FieldKind.TIMEDELTA

        assert field_kind(Seconds()) is FieldKind.TIMEDELTA
        assert field_kind(s.Float()) is FieldKind.FLOAT  # the base is untouched

    def test_a_kind_can_be_named_by_its_string(self):
        class Named(s.Str):
            KIND = 'path'

        assert Named.KIND is FieldKind.PATH
        assert field_kind(Named()) is FieldKind.PATH

    def test_a_subclass_can_have_no_kind(self):
        class Opaque(s.Str):
            KIND = None

        assert field_kind(Opaque()) is None

    def test_a_misspelt_kind_fails_where_it_is_declared(self):
        with pytest.raises(TypeError, match=r"Bad\.KIND: 'strr' is not a field kind; name one of 'int', "):

            class Bad(s.Str):
                KIND = 'strr'

    def test_a_direct_field_subclass_has_none_until_it_names_one(self):
        @dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
        class Raw(fields.Field):
            def serialize(self, value, validate=True, **kwargs):
                return value

            def deserialize(self, value, validate=True, **kwargs):
                return value

        @dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
        class Declared(Raw):
            KIND = FieldKind.DICT

        assert field_kind(Raw()) is None
        assert field_kind(Declared()) is FieldKind.DICT


def test_kind_is_a_class_attribute_not_a_field_option():
    assert 'KIND' not in {f.name for f in dataclasses.fields(s.Str())}
    with pytest.raises(TypeError, match='KIND'):
        s.Str(KIND=FieldKind.INT)  # ty: ignore[unknown-argument]


@pytest.mark.parametrize('other', [None, 'str', 3, object(), int], ids=repr)
def test_anything_that_isnt_a_field_has_no_kind(other):
    assert field_kind(other) is None


def test_the_package_root_exports_both():
    assert (s.FieldKind, s.field_kind) == (FieldKind, field_kind)
    # ``seared.fields.__all__`` is the registry of field classes, which these
    # aren't: they live at the root and in ``seared.fields.kind``.
    assert not {'FieldKind', 'field_kind'} & set(fields.__all__)
