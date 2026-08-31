"""Shared helpers for the per-format codecs.

Path-vs-content detection is the most important: every ``from_*``
method accepts either a path-like (read the file as UTF-8) or a string
of content (parse directly). Same rule across all formats so callers
don't have to remember per-format quirks.
"""
from __future__ import annotations

import os
from pathlib import Path


def read_source(source: str | os.PathLike) -> str:
    """Read a source as UTF-8 text.

    Detection rule:

    - If ``source`` is a string / ``PathLike`` AND points at an existing
      file, read the file.
    - Otherwise (string content that doesn't happen to be a file path),
      return it unchanged.

    Mirrors the precedent set by ``zeared.SessionConfig.from_yaml``.
    """
    if isinstance(source, (str, os.PathLike)) and Path(source).is_file():
        return Path(source).read_text(encoding='utf-8')
    if isinstance(source, str):
        return source
    msg = f'expected str path or content, got {type(source).__name__}'
    raise TypeError(msg)
