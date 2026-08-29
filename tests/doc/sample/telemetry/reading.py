import seared as s
from doc.sample.shared import Geo


@s.seared
class Reading(s.Seared):
    """One sensor reading."""

    source: str = s.Str(required=True)
    value: float = s.Float(required=True)
    where: Geo = s.T(Geo, required=True)
