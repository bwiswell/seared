"""Tests for ``seared/_core/__init__.py`` — the core's re-exports. Pins that
``__all__`` names exactly the four core types, and that each is the object its
own module defines.
"""

from __future__ import annotations

import importlib

import pytest

from seared import _core

#: Each re-exported name, and the module that defines it.
EXPORTS = {
    'Seared': 'base',
    'seared': 'decorator',
    'SearedError': 'errors',
    'ValidationError': 'errors',
}


class TestExports:
    def test_all_is_exactly_the_surface(self):
        assert sorted(_core.__all__) == sorted(EXPORTS)

    @pytest.mark.parametrize('name', sorted(EXPORTS))
    def test_each_name_is_its_modules_own(self, name):
        module = importlib.import_module(f'seared._core.{EXPORTS[name]}')
        assert getattr(_core, name) is getattr(module, name)
