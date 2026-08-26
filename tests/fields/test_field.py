"""Tests for ``seared.fields.field`` — the ``Field`` base class.

The base class is intentionally minimal: a frozen ``__slots__``
dataclass holding the orchestration knobs (``data_key``, ``keyed``,
``many``, ``required``, ``dump``, ``missing``) and abstract
``serialize`` / ``deserialize`` methods. Concrete behaviour lives in
each subclass file.
"""
from __future__ import annotations

import warnings

import pytest

from seared.fields.field import Field


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
