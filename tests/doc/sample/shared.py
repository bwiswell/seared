import seared as s


@s.seared
class Geo(s.Seared):
    """A geo point."""

    lat: float = s.Float(required=True, doc='degrees north')
    lon: float = s.Float(required=True)


@s.seared
class _Named(s.Seared):
    """Private base — should be excluded from the doc set."""

    name: str = s.Str(required=True)


@s.seared
class Widget(_Named):
    """A widget."""

    size: int = s.Int(default=1)
