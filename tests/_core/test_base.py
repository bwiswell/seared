"""Tests for ``seared._core.base.Seared`` — the marker base class for
seared dataclasses. Without the ``@seared`` decorator the class has
``__seared_fields__ = ()`` and ``dump``/``load`` raise
``NotImplementedError``. With the decorator (covered in
``test_decorator.py``) it gains the full serialisation surface.
"""

from __future__ import annotations

import inspect
import json
import math

import pytest

import seared as s
from seared._core.base import Seared


class TestBareSearedBase:
    def test_subclassing_works(self):
        class Foo(Seared):
            pass

        # The bare base has the empty ``__seared_fields__`` ClassVar.
        assert Foo.__seared_fields__ == ()

    def test_dump_raises_without_decorator(self):
        class Foo(Seared):
            pass

        with pytest.raises(NotImplementedError):
            Foo.dump(Foo())

    def test_load_raises_without_decorator(self):
        class Foo(Seared):
            pass

        with pytest.raises(NotImplementedError):
            Foo.load({})

    def test_dumps_loads_delegate_to_dump_load(self):
        """``dumps`` / ``loads`` are JSON convenience wrappers — they
        bottom out in the unimplemented dump/load, so they bubble the
        ``NotImplementedError`` out via the base class."""

        class Foo(Seared):
            pass

        with pytest.raises(NotImplementedError):
            Foo.dumps(Foo())
        with pytest.raises(NotImplementedError):
            Foo.loads('{}')


class TestDecoratedSearedBase:
    """Once decorated, the same base methods are replaced with real
    implementations — verified more thoroughly in test_decorator.py."""

    def test_decorated_dump_load_round_trip(self):
        @s.seared
        class Foo(s.Seared):
            x: int = s.Int(required=True)

        d = Foo.dump(Foo(x=1))
        assert d == {'x': 1}
        loaded = Foo.load(d)
        assert loaded.x == 1


@s.seared
class _Reading(s.Seared):
    sensor: str = s.Str(required=True)
    value: float = s.Float(required=True)


class TestDumpsPassesKwargsToJson:
    """Pin: ``dumps`` takes ``json.dumps``'s keyword arguments, as ``to_json`` does."""

    def test_formatting_options_reach_json(self):
        reading = _Reading(sensor='t1', value=1.5)
        assert _Reading.dumps(reading, sort_keys=True, separators=(',', ':')) == '{"sensor":"t1","value":1.5}'
        assert _Reading.dumps(reading, indent=2) == _Reading.to_json(reading, indent=2)

    @pytest.mark.parametrize(('value', 'token'), [(math.nan, 'NaN'), (math.inf, 'Infinity')])
    def test_non_finite_floats_are_written_bare_by_default(self, value, token):
        # Python's ``json`` default, kept: Python reads it back, and msgpack
        # and Python consumers carry these values on purpose.
        text = _Reading.dumps(_Reading(sensor='t1', value=value))
        assert f'"value": {token}' in text
        back = _Reading.loads(text).value
        assert math.isnan(back) if math.isnan(value) else back == value

    @pytest.mark.parametrize('value', [math.nan, math.inf])
    def test_allow_nan_false_refuses_them(self, value):
        reading = _Reading(sensor='t1', value=value)
        with pytest.raises(ValueError, match='not JSON compliant'):
            _Reading.dumps(reading, allow_nan=False)
        with pytest.raises(ValueError, match='not JSON compliant'):
            _Reading.to_json(reading, allow_nan=False)

    def test_no_kwargs_is_unchanged(self):
        reading = _Reading(sensor='t1', value=1.5)
        assert _Reading.dumps(reading) == json.dumps({'sensor': 't1', 'value': 1.5})


# ---------------------------------------------------------------------------
# The base declarations are the *typed* surface; the decorator attaches the
# real implementations at class-creation time. Nothing but these tests keeps
# the two in step, and when they drifted (0.2.8: base said `data`, the
# attached lambda took `d`) the result was code that type-checked and then
# raised TypeError — the worst of both.
# ---------------------------------------------------------------------------

CODEC_METHODS = [
    'to_json',
    'from_json',
    'to_toml',
    'from_toml',
    'to_yaml',
    'from_yaml',
    'to_csv',
    'from_csv',
]


@s.seared
class Sig(s.Seared):
    x: int = s.Int(required=True)


class TestBaseDeclarationsMatchImplementations:
    @pytest.mark.parametrize('name', ['dump', 'load'])
    def test_signatures_are_identical(self, name):
        declared = inspect.signature(getattr(s.Seared, name))
        attached = inspect.signature(getattr(Sig, name))
        assert declared.parameters.keys() == attached.parameters.keys()
        for param, decl in declared.parameters.items():
            assert decl.default == attached.parameters[param].default, param

    @pytest.mark.parametrize('name', ['dump', 'load'])
    def test_format_is_accepted_positionally_and_by_keyword(self, name):
        # zeared threads the carrier hint as a keyword; the bench and rusted's
        # own tests pass it positionally. Both have to work.
        params = inspect.signature(getattr(Sig, name)).parameters
        assert params['format'].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        assert params['format'].default == 'json'

    @pytest.mark.parametrize('name', CODEC_METHODS)
    def test_codec_params_are_callable_as_declared(self, name):
        # Weaker than identity: a codec impl may accept *more* (``to_json``
        # names ``indent``, which the base absorbs into ``**kwargs``). What
        # must hold is that anything the base promises actually exists.
        declared = inspect.signature(getattr(s.Seared, name))
        attached = inspect.signature(getattr(Sig, name))
        for param, decl in declared.parameters.items():
            if decl.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
                continue
            assert param in attached.parameters, f'{name}: base declares {param!r}, impl does not'


class TestDocumentedKeywordsWork:
    """The names above are API — these call through them, as a caller would."""

    def test_load_by_keyword(self):
        assert Sig.load(data={'x': 1}).x == 1

    def test_dump_by_keyword(self):
        assert Sig.dump(obj=Sig(x=1)) == {'x': 1}

    def test_format_by_keyword(self):
        assert Sig.dump(Sig(x=1), format='msgpack') == {'x': 1}
        assert Sig.load({'x': 1}, format='msgpack').x == 1


class TestIntrospectionSurfaces:
    """``__seared_fields__`` and ``__seared_accel__`` are declared on the base.

    Both are assigned by the decorator, but a surface that only exists after
    decoration is invisible to a type checker — callers reading it get an
    ``unresolved-attribute`` error and have to work around it. Declaring them
    with honest defaults costs nothing and makes the documented introspection
    actually usable. ``tests/typecheck/ok_idiom.py`` guards the typed half.
    """

    def test_base_has_defaults(self):
        assert s.Seared.__seared_fields__ == ()
        assert s.Seared.__seared_accel__.accelerated is False
        assert s.Seared.__seared_accel__.backend is None
        assert 'not decorated' in s.Seared.__seared_accel__.reason

    def test_undecorated_subclass_inherits_the_defaults(self):
        class Bare(s.Seared):
            pass

        assert Bare.__seared_fields__ == ()
        assert Bare.__seared_accel__.accelerated is False

    def test_decorator_replaces_both(self):
        @s.seared
        class Dec(s.Seared):
            x: int = s.Int(required=True)

        assert Dec.__seared_fields__ != ()
        # Whether it accelerated depends on the environment; that it is no
        # longer the base's "not decorated" placeholder does not.
        assert Dec.__seared_accel__ is not s.Seared.__seared_accel__
        assert Dec.__seared_accel__.reason != s.Seared.__seared_accel__.reason

    def test_accel_info_is_immutable(self):
        with pytest.raises((AttributeError, TypeError)):
            s.Seared.__seared_accel__.accelerated = True


class TestFieldSpec:
    """``FieldSpec`` names the ``(attr, wire, field)`` triple without changing it."""

    def test_is_still_a_triple(self):
        f = s.Int()
        spec = s.FieldSpec('x', 'ex', f)
        attr, wire, field = spec
        assert (attr, wire, field) == ('x', 'ex', f)
        assert spec == ('x', 'ex', f)
        assert len(spec) == 3

    def test_named_access(self):
        f = s.Str()
        spec = s.FieldSpec(attr='name', wire='n', field=f)
        assert (spec.attr, spec.wire, spec.field) == ('name', 'n', f)
