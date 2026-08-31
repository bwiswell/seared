"""Schema documentation generation for ``@seared`` classes.

- ``introspect(cls)`` → a structured :class:`SchemaDoc` (render-agnostic).
- ``document(cls)`` → a Markdown page for one class.
- ``build_docs(target)`` → ``{path: markdown}`` for a whole module/package.
- CLI: ``python -m seared.doc <module-or-package> [-o docs] [--check]``.

See project-plans/03-schema-docgen.md.
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
