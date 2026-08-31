"""Type-checker fixture: the canonical seared idiom must type-clean under ty.

Run by ``tests/typing/test_ty.py``. This file is intentionally NOT excluded
from ty — it is the thing under test. It must produce zero diagnostics.
"""

from enum import Enum
from typing import assert_type

import seared as s


class Color(Enum):
    RED = 0
    GREEN = 1


@s.seared
class Inner(s.Seared):
    x: int = s.Int(default=0)


@s.seared
class Outer(s.Seared):
    a: int = s.Int(default=5, doc='the a value')
    b: float = s.Float(default=3.14)
    c: str = s.Str(default='hello')
    d: Inner = s.T(Inner, required=True)
    e: Color = s.Enum(enum=Color, default=Color.GREEN)
    f: list[int] = s.Int(many=True, default_factory=list)
    g: dict[str, float] = s.Float(keyed=True, default_factory=dict)


# Construction is typed: keyword args are known, and defaulted fields are
# optional. `d` is required (no default) so it must be supplied.
obj = Outer(d=Inner(x=1))

# Attribute access carries the annotated type through — the second half of the
# original complaint (".load() results have no known attributes") is fixed.
assert_type(obj.a, int)
assert_type(obj.c, str)
assert_type(obj.d, Inner)
assert_type(obj.e, Color)
assert_type(obj.f, list[int])

# `.load` / `.loads` are visible classmethods.
loaded = Outer.load({'d': {'x': 2}})
assert_type(loaded.a, int)


# Parameterised decorator form also type-checks.
@s.seared(slots=False, validate=False)
class Lax(s.Seared):
    name: str = s.Str(default='x')


lax = Lax()
assert_type(lax.name, str)
