# `path.py` — `Path`

```python
location: pathlib.Path = s.Path(required=True)
```

`pathlib.Path` ↔ POSIX string. Always forward-slash on the wire
regardless of host OS — a Windows `WindowsPath('C:\\foo')` rounds
through as `'C:/foo'`.

## Receive-side type

Default: native `pathlib.Path` (`PosixPath` on Linux, `WindowsPath` on
Windows). For paths that must stay POSIX regardless of host, pass
`concrete=PurePosixPath`:

```python
opaque: PurePosixPath = s.Path(required=True, concrete=PurePosixPath)
```

## Wire format

Uses `value.as_posix()` — the standard Python idiom for "give me the
forward-slash string form of this path." Empty paths follow Python
semantics (`Path('')` → `Path('.')` → `'.'`).

## What this field doesn't do

- No `expanduser` / `resolve` — paths are wire-format-only; resolution
  policy is the user's call.
- No filesystem existence check on deserialize — the field accepts any
  string; existence is your problem.
