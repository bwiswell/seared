"""Tests for ``seared._core.base.Seared`` — the marker base class for
seared dataclasses. Without the ``@seared`` decorator the class has
``__seared_fields__ = ()`` and ``dump``/``load`` raise
``NotImplementedError``. With the decorator (covered in
``test_decorator.py``) it gains the full serialisation surface.
"""
from __future__ import annotations

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
