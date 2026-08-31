"""Pin: ``Path`` field — POSIX-normalised wire format; native ``Path``
on receive (or ``PurePosixPath`` via ``concrete=`` opt-in)."""

from __future__ import annotations

from pathlib import Path as P
from pathlib import PurePosixPath, PureWindowsPath

import pytest

import seared as s


@s.seared
class Document(s.Seared):
    location: P = s.Path(required=True)


@s.seared
class PosixDocument(s.Seared):
    location: PurePosixPath = s.Path(required=True, concrete=PurePosixPath)


class TestPosixWireFormat:
    def test_round_trip_simple(self):
        d = Document(location=P('a/b/c.txt'))
        out = Document.dump(d)
        assert out == {'location': 'a/b/c.txt'}
        loaded = Document.load(out)
        assert loaded.location == P('a/b/c.txt')

    def test_windows_path_normalises_to_forward_slash(self):
        # Construct a Windows-style path explicitly via PureWindowsPath
        # and verify the wire form is forward-slash POSIX. Tests the
        # normalisation path even when running on Linux.
        win = PureWindowsPath('C:\\foo\\bar\\baz.txt')
        # Substitute on the dataclass via Document.dump — the field
        # accepts any PurePath subclass.
        d = Document.__new__(Document)
        # Manual construction — bypasses the type hint, which is P (native).
        # Decorated init would coerce; for this round-trip we just dump.
        object.__setattr__(d, 'location', win)
        out = Document.dump(d)
        assert out['location'] == 'C:/foo/bar/baz.txt'

    def test_empty_path_round_trips_as_dot(self):
        # Python semantics: P('') → P('.') round-trips through wire.
        d = Document(location=P())
        out = Document.dump(d)
        # P('') stringifies to '.' via parts=('',) → PosixPath('.').
        # Document the round-trip target.
        loaded = Document.load(out)
        assert str(loaded.location) == '.'


class TestConcreteOverride:
    def test_pure_posix_path_stays_posix(self):
        d = PosixDocument(location=PurePosixPath('foo/bar'))
        loaded = PosixDocument.load(PosixDocument.dump(d))
        assert isinstance(loaded.location, PurePosixPath)
        assert str(loaded.location) == 'foo/bar'


class TestValidation:
    def test_serialize_rejects_non_path(self):
        d = Document.__new__(Document)
        object.__setattr__(d, 'location', 'not-a-path')
        with pytest.raises(s.ValidationError, match=r'expected pathlib\.Path'):
            Document.dump(d)

    def test_deserialize_rejects_non_string(self):
        with pytest.raises(s.ValidationError, match='expected str'):
            Document.load({'location': 12345})

    def test_deserialize_passes_through_existing_path(self):
        # If the dict carries an already-Path value (round-trip from
        # in-process load), deserialise accepts it.
        existing = P('/tmp/x.txt')
        out = Document.load({'location': existing})
        assert out.location == existing
