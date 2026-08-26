"""Type-checker fixture: usages that MUST raise ty diagnostics.

Proves the checking is real — the transform makes seared classes strict enough
to catch genuine mistakes, not merely silence `invalid-assignment`. Each marked
line names the diagnostic ``tests/typing/test_ty.py`` asserts on.
"""
import seared as s


@s.seared
class Point(s.Seared):
    x: int = s.Int(required=True)   # no default -> required
    y: int = s.Int(default=0)


# ERROR[missing-argument]: `x` is required and omitted.
p = Point(y=2)

# ERROR[unknown-argument]: `z` is not a field.
q = Point(x=1, z=9)

# ERROR[unresolved-attribute]: `.nope` is not an attribute of Point.
_ = Point(x=1).nope
