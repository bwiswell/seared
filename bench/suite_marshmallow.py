"""marshmallow case — equivalent schema, apples-to-apples with seared.

marshmallow is not a seared dependency; install via ``uv sync --extra bench``.
"""

from __future__ import annotations

from marshmallow import EXCLUDE, Schema
from marshmallow.fields import Float, Integer, List, Nested, String

from .harness import Case, dist_version


class InnerSchema(Schema):
    class Meta:
        """Ignore unknown keys, matching seared's load behaviour."""

        unknown = EXCLUDE

    x = Integer(required=True)
    y = Float(required=True)
    label = String(load_default=None)


class OuterSchema(Schema):
    class Meta:
        """Ignore unknown keys, matching seared's load behaviour."""

        unknown = EXCLUDE

    name = String(required=True)
    items = List(Nested(InnerSchema()), required=True)
    tags = List(String(), load_default=[])


def cases() -> list[Case]:
    """The marshmallow comparator case."""
    schema = OuterSchema()
    return [
        Case(
            library='marshmallow',
            variant='default',
            version=dist_version('marshmallow'),
            load=schema.load,
            dump=schema.dump,
        )
    ]
