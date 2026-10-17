# `enum_.py` — `Enum`

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
enums, int for `IntEnum` / int-valued enums). `enum=` is required:
`s.Enum()` without it raises `TypeError`.

`load` takes a member as is, and otherwise looks the wire value up with
`Color(value)`. For a string-valued enum that match is exact: `'red'`
finds `RED`, and neither the member name `'RED'` nor `'Red'` does. A
strict `dump` refuses anything but a member; lax mode writes the value it
was given.

An int-valued enum takes the values an [`Int`](int_.md) would, by the same
mode's rules: `2`, `'2'` and `2.0` in both modes, while `2.9` and `True`
are refused in strict mode and read as `2` and `1` in lax mode. `inf` is
refused in both. Any refusal reads `2.9 is not a valid Color`. Before
0.4.0, strict mode truncated `2.9` and read `True` as `1`, and `inf`
raised a bare `OverflowError`.
