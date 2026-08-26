"""Tests for ``seared/seared.py`` — the public re-export module
(``Seared`` base class + ``@seared`` decorator). The heavy decorator
behavior tests live in ``tests/_core/test_decorator.py``; this file
covers the package-level surface and version pin.
"""
from __future__ import annotations

import seared as s


def test_version():
    assert s.__version__ == '0.2.1'


class TestPublicSurface:
    def test_seared_decorator_re_exported(self):
        assert callable(s.seared)

    def test_seared_base_class_re_exported(self):
        assert isinstance(s.Seared, type)

    def test_decorator_on_seared_subclass_works(self):
        @s.seared
        class Smoke(s.Seared):
            x: int = s.Int(required=True)

        f = Smoke(x=1)
        assert Smoke.dump(f) == {'x': 1}
        assert Smoke.load({'x': 2}).x == 2

    def test_field_types_re_exported(self):
        # Spot-check a representative subset — full per-field tests
        # live under tests/fields/.
        for name in ('Bool', 'Bytes', 'Date', 'DateTime', 'Decimal',
                     'Dict', 'Enum', 'Field', 'Float', 'Int', 'Path',
                     'Str', 'T', 'Time', 'TimeDelta', 'Tuple', 'Union',
                     'UUID'):
            assert hasattr(s, name), f'seared package missing {name}'

    def test_optional_field_types_present(self):
        # NDArray / PandasFrame / PolarsFrame are always re-exported,
        # even when extras are missing — they fall back to a stub that
        # raises on instantiation. The attribute is always there.
        for name in ('NDArray', 'PandasFrame', 'PolarsFrame'):
            assert hasattr(s, name)

    def test_errors_re_exported(self):
        assert issubclass(s.ValidationError, s.SearedError)
        assert issubclass(s.SearedError, ValueError)
