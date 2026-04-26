# `bytes.py` — `Bytes`

```python
payload: bytes = s.Bytes(required=True)               # base64 default
hash_:   bytes = s.Bytes(required=True, encoding='hex')
```

Python `bytes` ↔ JSON-safe text encoding. `encoding='base64'` (default)
or `encoding='hex'`.

## `format='msgpack'` opt-out from text encoding

When the carrier supports raw bytes (msgpack does, JSON doesn't), pass
`format='msgpack'` to `dump` / `load` to bypass base64 / hex and emit
native `bytes` directly. Saves the ~33% encoding overhead.

```python
Blob.dump(b, format='json')      # → {'payload': 'aGVsbG8='}
Blob.dump(b, format='msgpack')   # → {'payload': b'hello'}
```

`format='json'` is the default — existing JSON consumers see no change.
