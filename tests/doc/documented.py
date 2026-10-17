"""A fixture with a ``doc=`` on every field, for ``--require-docs``."""

from __future__ import annotations

import seared as s


@s.seared
class Point(s.Seared):
    """A point on the floor plan."""

    x: float = s.Float(required=True, doc='east of the origin, in metres')
    y: float = s.Float(required=True, doc='north of the origin, in metres')
