from __future__ import annotations

#: One step of an error's path: a wire key or attribute name, a keyed-dict
#: key, or a list / tuple / record index.
type PathSegment = str | int


class SearedError(ValueError):
    """Base exception for all seared load/dump failures."""


class ValidationError(SearedError):
    """Raised when a value fails schema validation (missing required key, type mismatch, bad enum member, etc.).

    Carries its location as parts, and formats its message from them:

    - ``reason``: what went wrong, e.g. ``cannot deserialize 'x' as int``.
    - ``path``: where, as a tuple of keys and indices. On ``load`` they
      address the input the caller passed in (wire keys, list indices,
      keyed-dict keys), so ``functools.reduce(operator.getitem, err.path,
      data)`` retrieves the offending value. On ``dump`` they are attribute
      names.
    - ``cls_name``: the outermost class whose ``load`` / ``dump`` the error
      passed through, or ``None`` for an error raised outside one (a direct
      ``Field.deserialize`` call).

    ``str(err)`` reads ``Outer.items[1].n: cannot deserialize 'x' as int``;
    with an empty path, ``Outer: …``; with no class, the bare reason.
    ``ValidationError('reason')`` still works, with no path and no class.
    """

    def __init__(self, reason: str, *, path: tuple[PathSegment, ...] = (), cls_name: str | None = None) -> None:
        """Hold the parts, and format the message from them."""
        self.reason = reason
        self.path = tuple(path)
        self.cls_name = cls_name
        super().__init__(_format(reason, self.path, cls_name))

    def __reduce__(self) -> tuple:
        """Pickle by parts; the default pickles only ``args``, which would lose them."""
        return (_rebuild, (type(self), self.reason, self.path, self.cls_name))


def add_location(error: ValidationError, *segments: PathSegment, cls_name: str | None = None) -> None:
    """Prepend ``segments`` to ``error``'s path, and set its class, as it passes back up.

    In place, so the traceback and any ``__cause__`` survive. Each enclosing
    ``load`` / ``dump`` sets ``cls_name``, so the last one set, the outermost
    class, is the one the message names.
    """
    error.path = (*segments, *error.path)
    if cls_name is not None:
        error.cls_name = cls_name
    error.args = (_format(error.reason, error.path, error.cls_name),)


def _rebuild(
    cls: type[ValidationError],
    reason: str,
    path: tuple[PathSegment, ...],
    cls_name: str | None,
) -> ValidationError:
    return cls(reason, path=path, cls_name=cls_name)


def render_path(path: tuple[PathSegment, ...]) -> str:
    """Render a path for a message: ``items[1].n``, ``readers['r-1'].port``, ``[41].port``.

    A string that is a Python identifier reads as ``.name``; any other key
    as ``[repr(key)]``; an index as ``[i]``. A leading dot is dropped.
    """
    out = []
    for segment in path:
        if isinstance(segment, int) and not isinstance(segment, bool):
            out.append(f'[{segment}]')
        elif isinstance(segment, str) and segment.isidentifier():
            out.append(f'.{segment}')
        else:
            out.append(f'[{segment!r}]')
    return ''.join(out).removeprefix('.')


def _format(reason: str, path: tuple[PathSegment, ...], cls_name: str | None) -> str:
    rendered = render_path(path)
    if cls_name is None:
        return f'{rendered}: {reason}' if rendered else reason
    if not rendered:
        return f'{cls_name}: {reason}'
    separator = '' if rendered.startswith('[') else '.'
    return f'{cls_name}{separator}{rendered}: {reason}'
