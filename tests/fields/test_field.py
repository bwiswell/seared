"""Tests for ``seared.fields.field`` — the ``Field`` base class.

The base class is intentionally minimal: a frozen ``__slots__``
dataclass holding the orchestration knobs (``data_key``, ``keyed``,
``many``, ``required``, ``dump``, ``missing``) and abstract
``serialize`` / ``deserialize`` methods. Concrete behaviour lives in
each subclass file.
"""

from __future__ import annotations

import enum
import warnings

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
        assert f.dump is True
        assert f.missing is None

    def test_explicit_construction(self):
        f = Field(
            data_key='wire',
            keyed=True,
            many=False,
            required=True,
            dump=False,
            missing=42,
        )
        assert f.data_key == 'wire'
        assert f.keyed is True
        assert f.required is True
        assert f.dump is False
        assert f.missing == 42


class TestDefaultResolution:
    """`default=` / `default_factory=` are the canonical default kwargs;
    `missing=` is a deprecated alias resolved into `.missing`."""

    def test_default_folds_into_missing(self):
        f = Field(default=7)
        assert f.missing == 7
        assert f.default_factory is None

    def test_default_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            Field(default='x')  # must not raise

    def test_default_factory_is_retained_not_resolved(self):
        # The decorator invokes the factory per-instance; the field itself
        # keeps the callable and leaves `.missing` untouched.
        f = Field(default_factory=list)
        assert f.default_factory is list
        assert f.missing is None

    def test_missing_alias_still_works_but_warns(self):
        with pytest.warns(DeprecationWarning, match='missing='):
            f = Field(missing=42)
        assert f.missing == 42

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
    def test_missing_warning_points_at_the_caller(self, build):
        # Not at the dataclass-generated ``__init__`` (``<string>``) or a
        # seared module: those frames hid the warning under default filters
        # and pointed anyone who did see it at the wrong file.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            build()
        assert [w.filename for w in caught] == [__file__]

    def test_missing_warning_in_a_class_body_points_at_it(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')

            @s.seared
            class Legacy(s.Seared):
                x: int = s.Int(missing=3)

        assert [w.filename for w in caught] == [__file__]
        assert Legacy().x == 3

    def test_no_default_no_warning(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            f = Field()  # bare field — nothing set, must not warn
        assert f.missing is None


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
