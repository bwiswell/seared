"""Tests for ``seared.fields.field`` — the ``Field`` base class.

The base class is intentionally minimal: a frozen ``__slots__``
dataclass holding the orchestration knobs (``data_key``, ``keyed``,
``many``, ``required``, ``dump``, ``default``, ``default_factory``) and
abstract ``serialize`` / ``deserialize`` methods. Concrete behaviour lives
in each subclass file.
"""

from __future__ import annotations

import enum

import pytest

import seared as s
from seared.fields.field import Field


class _Color(enum.Enum):
    RED = 'r'


class TestFieldDefaults:
    def test_default_construction(self):
        f = Field()
        assert f.data_key is None
        assert f.keyed is False
        assert f.many is False
        assert f.required is False
        assert f.nullable is False
        assert f.dump is True
        assert f.default is None
        assert f.default_factory is None

    def test_explicit_construction(self):
        f = Field(
            data_key='wire',
            keyed=True,
            many=False,
            required=True,
            nullable=True,
            dump=False,
            default=42,
        )
        assert f.data_key == 'wire'
        assert f.keyed is True
        assert f.required is True
        assert f.nullable is True
        assert f.dump is False
        assert f.default == 42


class TestDefaultResolution:
    """`default=` / `default_factory=` are the only default kwargs; `missing=` was removed in 0.4.0."""

    def test_default_is_held_as_given(self):
        f = Field(default=7)
        assert f.default == 7
        assert f.default_factory is None

    def test_default_factory_is_retained_not_resolved(self):
        # The decorator invokes the factory per instance; the field keeps the callable.
        f = Field(default_factory=list)
        assert f.default_factory is list
        assert f.default is None

    @pytest.mark.parametrize(
        'build',
        [
            lambda: Field(missing=1),
            lambda: s.Int(missing=1),
            lambda: s.T(s.Seared, missing=1),
            lambda: s.Tuple(s.Int(), missing=(1,)),
            lambda: s.Enum(enum=_Color, missing=_Color.RED),
        ],
        ids=['Field', 'Int', 'T', 'Tuple', 'Enum'],
    )
    def test_the_missing_keyword_is_gone(self, build):
        # Removed outright: Python's own TypeError, no custom pointer.
        with pytest.raises(TypeError, match='missing'):
            build()

    def test_a_subclass_can_still_call_super_post_init(self):
        # ``Field.__post_init__`` has nothing to do now, but stays so a
        # subclass written against the old base keeps working.
        Field().__post_init__()
        assert s.Enum(enum=_Color, default=_Color.RED).default is _Color.RED


class TestFieldFrozen:
    def test_field_is_frozen(self):
        f = Field()
        with pytest.raises((AttributeError, TypeError)):
            # frozen=True dataclass — can't reassign.
            f.required = True  # type: ignore[misc]


class TestAbstractMethods:
    def test_serialize_raises_not_implemented(self):
        f = Field()
        with pytest.raises(NotImplementedError):
            f.serialize('anything')

    def test_deserialize_raises_not_implemented(self):
        f = Field()
        with pytest.raises(NotImplementedError):
            f.deserialize('anything')
