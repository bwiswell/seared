"""Tests for ``seared.fields.field`` — the ``Field`` base class.

The base class is intentionally minimal: a frozen ``__slots__``
dataclass holding the orchestration knobs (``data_key``, ``keyed``,
``many``, ``required``, ``dump``, ``missing``) and abstract
``serialize`` / ``deserialize`` methods. Concrete behaviour lives in
each subclass file.
"""
from __future__ import annotations

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
