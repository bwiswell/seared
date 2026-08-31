"""Type-checker fixture: usages that MUST raise ty diagnostics.

Proves the checking is real — the transform makes seared classes strict enough
to catch genuine mistakes, not merely silence `invalid-assignment`. Each marked
line names the diagnostic ``tests/typing/test_ty.py`` asserts on.
"""

import seared as s


@s.seared
class Point(s.Seared):
    x: int = s.Int(required=True)  # no default -> required
    y: int = s.Int(default=0)


# ERROR[missing-argument]: `x` is required and omitted.
p = Point(y=2)

# ERROR[unknown-argument]: `z` is not a field.
q = Point(x=1, z=9)

# ERROR[unresolved-attribute]: `.nope` is not an attribute of Point.
_ = Point(x=1).nope


class NotSeared:
    """A plain class — never decorated, so not a valid ``T`` target."""


# ERROR[invalid-argument-type]: `T` binds a *seared* class. Passing any other
# class used to type-check and then fail at runtime on `.dump`; `Union` has
# always demanded `type[Seared]`, and `T` now matches it.
@s.seared
class Holder(s.Seared):
    nested: object = s.T(NotSeared)
