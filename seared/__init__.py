from typing import Any

from ._core.accel import AccelInfo, accel_status
from ._core.errors import SearedError, ValidationError
from .doc import document, introspect
from .fields.bool_ import Bool
from .fields.bytes_ import Bytes
from .fields.date import Date
from .fields.datetime_ import DateTime
from .fields.decimal_ import Decimal
from .fields.dict_ import Dict
from .fields.enum_ import Enum
from .fields.field import Field
from .fields.float_ import Float
from .fields.int_ import Int
from .fields.path import Path
from .fields.str_ import Str
from .fields.t import T
from .fields.time_ import Time
from .fields.timedelta import TimeDelta
from .fields.tuple_ import Tuple
from .fields.union import Union
from .fields.uuid_ import UUID
from .seared import Seared, seared

try:
    from .fields.ndarray import NDArray
except ImportError:

    class NDArray:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Raise, naming the extra that would make this field real."""
            msg = "seared.NDArray requires numpy. Install it with: uv add 'seared[numpy]'"
            raise ImportError(msg)


try:
    from .fields.pandas_ import PandasFrame
except ImportError:

    class PandasFrame:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Raise, naming the extra that would make this field real."""
            msg = "seared.PandasFrame requires pandas. Install it with: uv add 'seared[pandas]'"
            raise ImportError(msg)


try:
    from .fields.polars_ import PolarsFrame
except ImportError:

    class PolarsFrame:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Raise, naming the extra that would make this field real."""
            msg = "seared.PolarsFrame requires polars. Install it with: uv add 'seared[polars]'"
            raise ImportError(msg)


__version__ = '0.2.8'

__all__ = [
    'UUID',
    'AccelInfo',
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
    'Seared',
    'SearedError',
    'Str',
    'T',
    'Time',
    'TimeDelta',
    'Tuple',
    'Union',
    'ValidationError',
    '__version__',
    'accel_status',
    'document',
    'introspect',
    'seared',
]
