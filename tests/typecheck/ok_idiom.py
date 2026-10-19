"""Type-checker fixture: the canonical seared idiom must type-clean under ty.

Run by ``tests/typecheck/test_ty.py``. This file is intentionally NOT excluded
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


# Introspection surfaces are declared on the base, so reading them
# type-checks. `__seared_accel__` was assigned only at decoration time until
# 0.3.0, which made every caller work around a checker error.
assert_type(Outer.__seared_accel__, s.AccelInfo)
assert_type(Outer.__seared_accel__.accelerated, bool)
assert_type(Outer.__seared_accel__.backend, str | None)
assert_type(Outer.__seared_accel__.reason, str | None)
assert_type(Outer.__seared_fields__, tuple[s.FieldSpec, ...])

# Each entry is a FieldSpec: named and typed, and still a 3-tuple.
spec = Outer.__seared_fields__[0]
assert_type(spec.attr, str)
assert_type(spec.wire, str)
assert_type(spec.field, s.Field)
attr, wire, field = spec
assert_type(field, s.Field)


# `nullable=True` makes `None` a value: the annotation says `| None`, and it's
# independent of `required`. A nullable required field must still be passed,
# but `None` is a legal argument for it.
@s.seared
class Nulls(s.Seared):
    maybe: int | None = s.Int(nullable=True, default=None)
    fallback: int | None = s.Int(nullable=True, default=5)
    must: int | None = s.Int(nullable=True, required=True)
    child: Inner | None = s.T(Inner, nullable=True, default=None)
    pair: tuple | None = s.Tuple(s.Int(), s.Int(), nullable=True, default=None)


nulls = Nulls(must=None)
assert_type(nulls.must, int | None)
assert_type(nulls.fallback, int | None)


# Bounds (0.4.4) are keyword options on `Int` and `Float`: an `int` bound on a
# `Float` is a `float` to the checker, as the numeric tower has it.
@s.seared
class Bounded(s.Seared):
    count: int = s.Int(ge=0, lt=10, default=0)
    ratio: float = s.Float(gt=0, le=1.0, required=True)
    scores: list[int] = s.Int(le=100, many=True, default_factory=list)


bounded = Bounded(ratio=0.5)
assert_type(bounded.count, int)
