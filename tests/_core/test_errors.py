"""Tests for ``seared._core.errors`` — the ``SearedError`` exception
hierarchy."""
from __future__ import annotations

import pytest

import seared as s
from seared._core.errors import SearedError, ValidationError


class TestExceptionHierarchy:
    def test_seared_error_subclasses_value_error(self):
        assert issubclass(SearedError, ValueError)

    def test_validation_error_subclasses_seared_error(self):
        assert issubclass(ValidationError, SearedError)

    def test_validation_error_isinstance_value_error(self):
        e = ValidationError('test')
        assert isinstance(e, ValueError)
        assert isinstance(e, SearedError)


class TestPackageReExports:
    def test_seared_error_re_exported(self):
        assert s.SearedError is SearedError

    def test_validation_error_re_exported(self):
        assert s.ValidationError is ValidationError


class TestRaiseAndCatch:
    def test_validation_error_caught_as_seared_error(self):
        with pytest.raises(SearedError):
            raise ValidationError('test')

    def test_validation_error_caught_as_value_error(self):
        with pytest.raises(ValueError):
            raise ValidationError('test')

    def test_validation_error_carries_message(self):
        try:
            raise ValidationError('descriptive message')
        except ValidationError as e:
            assert 'descriptive message' in str(e)
