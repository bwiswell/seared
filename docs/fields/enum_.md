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
