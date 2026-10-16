"""Tests for ``seared._core.errors`` — the ``SearedError`` exception
hierarchy, and how a ``ValidationError`` carries and renders its location."""

from __future__ import annotations

import pickle

import pytest

import seared as s
from seared._core.errors import SearedError, ValidationError, add_location, render_path


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
        msg = 'test'
        with pytest.raises(SearedError):
            raise ValidationError(msg)

    def test_validation_error_caught_as_value_error(self):
        msg = 'test'
        with pytest.raises(ValueError, match='test'):
            raise ValidationError(msg)

    def test_validation_error_carries_message(self):
        msg = 'descriptive message'
        with pytest.raises(ValidationError, match=msg):
            raise ValidationError(msg)


class TestParts:
    """Pin: a ``ValidationError`` carries its location as parts and formats its message from them."""

    def test_positional_construction_is_a_bare_reason(self):
        e = ValidationError('bad value')
        assert (e.reason, e.path, e.cls_name, str(e)) == ('bad value', (), None, 'bad value')

    def test_a_class_and_a_path(self):
        e = ValidationError('cannot deserialize', path=('items', 1, 'n'), cls_name='Outer')
        assert str(e) == 'Outer.items[1].n: cannot deserialize'
        assert e.path == ('items', 1, 'n')

    def test_a_class_and_no_path(self):
        assert str(ValidationError('expected dict, got list', cls_name='Outer')) == 'Outer: expected dict, got list'

    def test_a_path_and_no_class(self):
        # A field raising outside any ``load`` with a location of its own,
        # such as a ``Tuple`` slot.
        assert str(ValidationError('expected str, got int', path=(1,))) == '[1]: expected str, got int'

    @pytest.mark.parametrize(
        ('path', 'rendered'),
        [
            (('items', 1, 'n'), 'items[1].n'),
            (('readers', 'r-1', 'port'), "readers['r-1'].port"),
            ((41, 'port'), '[41].port'),
            (('a', 'b'), 'a.b'),
            (('my key', 0), "['my key'][0]"),
            ((), ''),
        ],
    )
    def test_render_path(self, path, rendered):
        assert render_path(path) == rendered

    def test_a_leading_index_joins_the_class_without_a_dot(self):
        assert str(ValidationError('x', path=(41, 'port'), cls_name='Row')) == 'Row[41].port: x'


class TestAddLocation:
    def test_prepends_and_reformats_in_place(self):
        e = ValidationError('bad', path=('n',), cls_name='Inner')
        add_location(e, 'items', 1, cls_name='Outer')
        assert (e.path, e.cls_name, str(e)) == (('items', 1, 'n'), 'Outer', 'Outer.items[1].n: bad')

    def test_without_a_class_keeps_the_one_it_had(self):
        e = ValidationError('bad', cls_name='Row')
        add_location(e, 3)
        assert str(e) == 'Row[3]: bad'

    def test_keeps_the_traceback_and_cause(self):
        def fail():
            try:
                int('x')
            except ValueError as cause:
                msg = 'bad'
                raise ValidationError(msg) from cause

        with pytest.raises(ValidationError) as info:
            fail()
        e = info.value
        tb, cause = e.__traceback__, e.__cause__
        add_location(e, 'n', cls_name='C')
        assert e.__traceback__ is tb
        assert isinstance(cause, ValueError)
        assert e.__cause__ is cause


class TestPickling:
    def test_round_trips_its_parts(self):
        e = ValidationError('bad', path=('items', 1, 'n'), cls_name='Outer')
        back = pickle.loads(pickle.dumps(e))
        assert type(back) is ValidationError
        assert (back.reason, back.path, back.cls_name, str(back)) == (e.reason, e.path, e.cls_name, str(e))
