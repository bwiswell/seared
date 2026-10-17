from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from seared._core.errors import ValidationError

from .field import Field
from .kind import FieldKind

try:
    import numpy as np

    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False


@dataclass(frozen=True, kw_only=True, slots=True)
class NDArray(Field):
    KIND = FieldKind.NDARRAY

    #: The element type (0.4.1). ``None`` infers it from the values, so a
    #: ``float32`` array comes back ``float64``; anything ``numpy.dtype()``
    #: accepts casts each load to it and checks each strict dump against it.
    dtype: Any = None

    def __post_init__(self) -> None:
        """Fail fast when the ``seared[numpy]`` extra isn't installed, and resolve ``dtype``."""
        super().__post_init__()
        if not _NUMPY_AVAILABLE:
            msg = "seared.NDArray requires numpy. Install it with: uv add 'seared[numpy]'"
            raise ImportError(msg)
        if self.dtype is not None:
            try:
                resolved = np.dtype(self.dtype)
            except TypeError as exc:
                msg = f'NDArray: dtype= takes a numpy dtype, got {self.dtype!r}'
                raise TypeError(msg) from exc
            object.__setattr__(self, 'dtype', resolved)

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:
        """``numpy.ndarray`` → nested lists.

        With a ``dtype``, a strict dump refuses an array of another dtype, and a
        lax one casts it first, as numpy casts.
        """
        if not isinstance(value, np.ndarray):
            if validate:
                msg = f'expected ndarray, got {type(value).__name__}'
                raise ValidationError(msg)
            return value
        if self.dtype is not None and value.dtype != self.dtype:
            if validate:
                msg = f'expected dtype {self.dtype}, got {value.dtype}'
                raise ValidationError(msg)
            with np.errstate(all='ignore'):
                value = value.astype(self.dtype)
        return value.tolist()

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:
        """Nested lists → ``numpy.ndarray``, cast to ``dtype`` when one is declared.

        A strict load casts only what it can carry over whole, as the scalar
        fields do: a ``bool`` isn't a number, a fractional or non-finite value
        isn't an integer, an integer must fit the type's range, a finite value
        must stay finite, and a ``bool`` dtype takes only ``0`` and ``1``.
        Narrowing a float's precision (``float64`` to ``float32``) is the point
        of declaring one, so it's allowed. The checks see the array numpy builds,
        not each element: an array of bools is refused, but a ``True`` among
        numbers is already a ``1``. A lax load casts as numpy casts.
        """
        if self.dtype is None:
            return np.array(value)
        try:
            raw = np.array(value)
        except ValueError as exc:  # ragged nesting
            msg = f'cannot load as an array: {exc}'
            raise ValidationError(msg) from exc
        if validate:
            _refuse_a_lossy_cast(raw, self.dtype)
        try:
            with np.errstate(all='ignore'):
                return raw.astype(self.dtype)
        except (ValueError, TypeError, OverflowError) as exc:
            msg = f'cannot deserialize as {self.dtype}: {exc}'
            raise ValidationError(msg) from exc


def _refuse_a_lossy_cast(raw: Any, target: Any) -> None:
    """Raise at the first element ``raw`` can't carry over to ``target`` whole.

    The error's path is that element's index, so it reads
    ``Cls.samples[1][2]: cannot deserialize 1.5 as int32``.
    """
    kind, source = target.kind, raw.dtype.kind
    if kind in 'iuf' and source == 'b':
        msg = f'expected numbers, got bool, for dtype {target}'
        raise ValidationError(msg)
    if source not in 'iuf':
        return  # strings and objects: the cast itself decides
    with np.errstate(all='ignore'):
        if kind in 'iu':
            info = np.iinfo(target)
            bad = (raw < info.min) | (raw > info.max)
            if source == 'f':
                bad |= ~np.isfinite(raw) | (raw != np.trunc(raw))
        elif kind == 'f':
            bad = np.isfinite(raw) & ~np.isfinite(raw.astype(target))
        elif kind == 'b':
            bad = (raw != 0) & (raw != 1)
        else:
            return
    if bad.any():
        index = tuple(int(i) for i in np.argwhere(bad)[0])
        msg = f'cannot deserialize {raw[index].item()!r} as {target}'
        raise ValidationError(msg, path=index)
