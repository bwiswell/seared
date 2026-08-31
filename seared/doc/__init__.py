"""Schema documentation generation for ``@seared`` classes.

- ``introspect(cls)`` → a structured :class:`SchemaDoc` (render-agnostic).
- ``document(cls)`` → a Markdown page for one class.
- ``build_docs(target)`` → ``{path: markdown}`` for a whole module/package.
- CLI: ``python -m seared.doc <module-or-package> [-o docs] [--check]``.

The two stages are deliberately separate: ``introspect`` produces a
render-agnostic :class:`SchemaDoc` tree, and renderers consume *that* rather
than the classes themselves. It is what lets a downstream package layer its
own renderer (zeared's wire-aware one) on the same intermediate, and what
would let a JSON-Schema or HTML output land without touching introspection.
"""

from .generate import build_docs, collect, main
from .introspect import (
    EnumDoc,
    FieldDoc,
    SchemaDoc,
    VariantDoc,
    introspect,
    is_seared_class,
)
from .render import (
    document,
    render_enums,
    render_fields_table,
    render_header,
    render_schema,
    render_variants,
)

__all__ = [
    'EnumDoc',
    'FieldDoc',
    'SchemaDoc',
    'VariantDoc',
    'build_docs',
    'collect',
    'document',
    'introspect',
    'is_seared_class',
    'main',
    'render_enums',
    'render_fields_table',
    'render_header',
    'render_schema',
    'render_variants',
]
