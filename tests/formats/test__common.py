"""Tests for ``seared.formats._common.read_source`` — the path-vs-content
detection helper used by every codec's ``from_*`` method.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from seared.formats._common import read_source


class TestPathSource:
    def test_reads_existing_file(self):
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', suffix='.txt', delete=False,
        ) as fh:
            fh.write('file-content-payload')
            tmp_path = fh.name
        try:
            assert read_source(tmp_path) == 'file-content-payload'
        finally:
            Path(tmp_path).unlink()

    def test_accepts_pathlike(self):
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', suffix='.txt', delete=False,
        ) as fh:
            fh.write('via-pathlib')
            tmp_path = fh.name
        try:
            assert read_source(Path(tmp_path)) == 'via-pathlib'
        finally:
            Path(tmp_path).unlink()

    def test_utf8_round_trip(self):
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', suffix='.txt', delete=False,
        ) as fh:
            fh.write('emoji-✨ and 中文')
            tmp_path = fh.name
        try:
            assert read_source(tmp_path) == 'emoji-✨ and 中文'
        finally:
            Path(tmp_path).unlink()


class TestContentSource:
    def test_passthrough_for_non_path_string(self):
        # A string that doesn't happen to be a file path — return as-is.
        content = '{"already": "content"}'
        assert read_source(content) == content

    def test_multiline_content_passthrough(self):
        content = 'line one\nline two\nline three\n'
        assert read_source(content) == content


class TestRejected:
    def test_non_string_non_pathlike_raises(self):
        with pytest.raises(TypeError, match='expected str path or content'):
            read_source(42)  # type: ignore[arg-type]

    def test_bytes_rejected(self):
        with pytest.raises(TypeError, match='expected str path or content'):
            read_source(b'bytes-not-supported')  # type: ignore[arg-type]
