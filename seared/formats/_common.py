"""Shared helpers for the per-format codecs.

Path-vs-content detection is the most important: every ``from_*``
method accepts either a path-like (read the file as UTF-8) or a string
of content (parse directly). Same rule across all formats so callers
don't have to remember per-format quirks.
"""
from __future__ import annotations

import os
from typing import Union


def read_source(source: Union[str, 'os.PathLike']) -> str:
    """Read a source as UTF-8 text. Detection rule:

    - If ``source`` is a string / ``PathLike`` AND points at an existing
      file, read the file.
    - Otherwise (string content that doesn't happen to be a file path),
      return it unchanged.

    Mirrors the precedent set by ``zeared.SessionConfig.from_yaml``.
    """
    if isinstance(source, (str, os.PathLike)) and os.path.isfile(source):
        with open(source, 'r', encoding='utf-8') as f:
            return f.read()
    if isinstance(source, str):
        return source
    raise TypeError(
        f'expected str path or content, got {type(source).__name__}'
    )
