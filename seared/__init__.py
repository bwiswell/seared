from .bool import Bool
from .bytes import Bytes
from .date import Date
from ._datetime import DateTime
from ._dict import Dict
from ._enum import Enum
from .float import Float
from .int import Int
from .seared import Seared, seared
from .str import Str
from .t import T
from .time import Time
from .timedelta import TimeDelta
from .tuple import Tuple
from .uuid import UUID

try:
    from .ndarray import NDArray
except ImportError:
    class NDArray:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "seared.NDArray requires numpy. "
                "Install it with: uv add 'seared[numpy]'"
            )


__version__ = '0.2.0'
