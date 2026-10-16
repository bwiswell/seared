# `_enum.py` — `Enum`

```python
import enum

class Color(enum.Enum):
    RED = 'red'
    BLUE = 'blue'

@s.seared
class Brush(s.Seared):
    color: Color = s.Enum(enum=Color, required=True)
```

`enum.Enum` ↔ underlying `value` on the wire (string for `str`-valued
enums, int for `IntEnum` / int-valued enums). Auto-coerces strings on
deserialize for ergonomic round-trip.

An int-valued enum takes the values an [`Int`](int_.md) would, by the same
mode's rules: `2`, `'2'` and `2.0` in both modes, while `2.9` and `True`
are refused in strict mode and read as `2` and `1` in lax mode. `inf` is
refused in both. Any refusal reads `2.9 is not a valid Color`. Before
0.4.0, strict mode truncated `2.9` and read `True` as `1`, and `inf`
raised a bare `OverflowError`.
