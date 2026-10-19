"""Type-checker fixture: usages that MUST raise ty diagnostics.

Proves the checking is real — the transform makes seared classes strict enough
to catch genuine mistakes, not merely silence `invalid-assignment`. Each marked
line names the diagnostic ``tests/typecheck/test_ty.py`` asserts on.
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


# ERROR[unknown-argument]: `missing=` was removed in 0.4.0; the spelling is
# `default=` (or `default_factory=` for a mutable default).
@s.seared
class Legacy(s.Seared):
    x: int = s.Int(missing=3)


@s.seared
class _Start(s.Seared):
    speed: float = s.Float(default=0.0)


# ERROR[unknown-argument]: a `Union` can't be nullable (its envelope spans the
# parent's keys, so no one key carries the `null`); it raises at runtime too.
@s.seared
class Envelope(s.Seared):
    action: object = s.Union(variants={'start': _Start}, nullable=True)


# ERROR[invalid-argument-type]: an `Int`'s bounds are `int`s (0.4.4); it raises
# at runtime too.
@s.seared
class HalfBound(s.Seared):
    x: int = s.Int(ge=0.5, default=1)


# ERROR[unknown-argument]: the option is `ge=`, not `gte=`.
@s.seared
class Misspelt(s.Seared):
    x: int = s.Int(gte=0, default=1)
