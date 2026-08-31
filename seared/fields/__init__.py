"""Field type registry — every ``Field`` subclass shipped with seared.

Importing from this namespace works as a parallel surface to the package
root: ``from seared.fields import Bool`` is equivalent to ``from seared
import Bool``. The optional dataframe / numpy fields gracefully degrade
to ImportError-on-instantiate stubs when their extras aren't installed,
mirroring the package-init's behavior.
"""

from typing import Any

from .bool_ import Bool
from .bytes_ import Bytes
from .date import Date
from .datetime_ import DateTime
from .decimal_ import Decimal
from .dict_ import Dict
from .enum_ import Enum
from .field import Field
from .float_ import Float
from .int_ import Int
from .path import Path
from .str_ import Str
from .t import T
from .time_ import Time
from .timedelta import TimeDelta
from .tuple_ import Tuple
from .union import Union
from .uuid_ import UUID

try:
    from .ndarray import NDArray
except ImportError:

    class NDArray:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Raise, naming the extra that would make this field real."""
            msg = "seared.NDArray requires numpy. Install it with: uv add 'seared[numpy]'"
            raise ImportError(msg)


try:
    from .pandas_ import PandasFrame
except ImportError:

    class PandasFrame:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Raise, naming the extra that would make this field real."""
            msg = "seared.PandasFrame requires pandas. Install it with: uv add 'seared[pandas]'"
            raise ImportError(msg)


try:
    from .polars_ import PolarsFrame
except ImportError:

    class PolarsFrame:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Raise, naming the extra that would make this field real."""
            msg = "seared.PolarsFrame requires polars. Install it with: uv add 'seared[polars]'"
            raise ImportError(msg)


__all__ = [
    'UUID',
    'Bool',
    'Bytes',
    'Date',
    'DateTime',
    'Decimal',
    'Dict',
    'Enum',
    'Field',
    'Float',
    'Int',
    'NDArray',
    'PandasFrame',
    'Path',
    'PolarsFrame',
    'Str',
    'T',
    'Time',
    'TimeDelta',
    'Tuple',
    'Union',
]
