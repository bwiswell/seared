"""Tests for ``seared/doc/__init__.py`` — the ``seared.doc`` surface. Pins its
exports: ``__all__`` names exactly the public API, and each name is the object
its own module defines, so a rename there can't leave a stale re-export.

The modules come from ``importlib``: ``seared.doc.introspect`` is also the name
of a re-exported function, which shadows the submodule as an attribute.
"""

from __future__ import annotations

import importlib

import pytest

import seared.doc as doc

#: Each public name, and the module that defines it.
EXPORTS = {
    'EnumDoc': 'introspect',
    'FieldDoc': 'introspect',
    'SchemaDoc': 'introspect',
    'VariantDoc': 'introspect',
    'introspect': 'introspect',
    'is_seared_class': 'introspect',
    'build_docs': 'generate',
    'collect': 'generate',
    'main': 'generate',
    'document': 'render',
    'render_enums': 'render',
    'render_fields_table': 'render',
    'render_header': 'render',
    'render_schema': 'render',
    'render_variants': 'render',
}


class TestExports:
    def test_all_is_exactly_the_surface(self):
        assert sorted(doc.__all__) == sorted(EXPORTS)

    @pytest.mark.parametrize('name', sorted(EXPORTS))
    def test_each_name_is_its_modules_own(self, name):
        module = importlib.import_module(f'seared.doc.{EXPORTS[name]}')
        assert getattr(doc, name) is getattr(module, name)
