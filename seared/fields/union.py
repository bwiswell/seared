from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from seared._core.base import Seared

from seared._core.errors import ValidationError, add_location

from .field import Field


@dataclass(frozen=True, kw_only=True, slots=True)
class Union(Field):
    """Tagged-union field — the ``{tag, payload}`` envelope pattern.

    The value of a ``Union`` field is an instance of one of the declared
    variant classes. On the wire, it serialises as an envelope with a
    discriminator key (``tag_key``) naming the variant and either:

    - ``payload_key`` set (nested): the variant's payload lives under
      ``payload_key`` — ``{"action": "start", "args": {"speed": 10}}``.
    - ``payload_key=None`` (flat): the variant's fields are merged at the
      same level as the tag — ``{"type": "start", "speed": 10}``.

    ``Union`` is an ``UNWRAP`` field: the seared decorator merges the
    envelope at the parent class's top-level wire dict rather than nesting
    it under a wire key. A class can hold several ``UNWRAP`` fields, as long
    as their ``tag_key`` / ``payload_key`` wire keys don't collide.

    Unknown tags on load raise ``ValidationError`` by default. Pass
    ``fallback=<VariantCls>`` to enable graceful schema-evolution
    fallback: unknown tags coerce to the named variant rather
    than raising. Useful when older consumers may receive newer
    schemas — they decode what they can recognise and route the rest
    to a generic / sentinel variant.

    A value instance whose type isn't one of the declared variants
    also raises ``ValidationError`` on serialize (strict).
    """

    variants: dict[str, type[Seared]]
    tag_key: str = 'type'
    payload_key: str | None = None
    fallback: type[Seared] | None = None

    UNWRAP: ClassVar[bool] = True

    def __post_init__(self) -> None:
        """Validate the declared tag → variant-class mapping."""
        if not self.variants:
            msg = 'Union: variants mapping must be non-empty'
            raise TypeError(msg)
        for tag, cls in self.variants.items():
            if not isinstance(tag, str) or not tag:
                msg = f'Union: tag must be a non-empty string, got {tag!r}'
                raise TypeError(msg)
            if not isinstance(cls, type):
                msg = f'Union: variant for tag {tag!r} must be a class, got {cls!r}'
                raise TypeError(msg)
        if self.fallback is not None and not isinstance(self.fallback, type):
            msg = f'Union: fallback must be a class, got {self.fallback!r}'
            raise TypeError(msg)
        # Until 0.4.0, ``default=`` named the fallback variant. It now means
        # what it means on every other field, the value an absent key gets,
        # which a Union doesn't have: its envelope is always populated on load,
        # and absent from a constructor call it's ``None``. Refused by name, so
        # an old ``default=Variant`` can't quietly change meaning.
        for option in ('default', 'default_factory'):
            if getattr(self, option) is not None:
                msg = (
                    f'Union: {option}= is not supported, since a Union has no default value; '
                    f'to fall back to a variant on an unknown tag, use fallback=<VariantCls>'
                )
                raise TypeError(msg)
        # A Union's envelope spans its parent's keys (the tag, and the payload
        # key or the variant's own fields), so there is no one key a ``null``
        # could sit on.
        if self.nullable:
            msg = 'Union: nullable= is not supported, since a Union has no single wire key to carry a null'
            raise TypeError(msg)

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> dict:
        """Variant instance → the ``{tag, payload}`` envelope (flat or nested)."""
        for tag, variant_cls in self.variants.items():
            if isinstance(value, variant_cls):
                payload = variant_cls.dump(value, kwargs.get('format', 'json'))
                if self.payload_key is None:
                    # Flat: merge tag + payload at top level.
                    if self.tag_key in payload:
                        msg = (
                            f'Union: flat envelope collides — variant '
                            f'{variant_cls.__name__} has a field named '
                            f'{self.tag_key!r}'
                        )
                        raise ValidationError(msg)
                    return {self.tag_key: tag, **payload}
                return {self.tag_key: tag, self.payload_key: payload}
        if validate:
            names = [v.__name__ for v in self.variants.values()]
            msg = f'Union: value of type {type(value).__name__} does not match any declared variant ({names})'
            raise ValidationError(msg)
        return {}

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:
        """A ``{tag, payload}`` envelope → the tagged variant instance."""
        if not isinstance(value, dict):
            if validate:
                msg = f'Union: expected dict, got {type(value).__name__}'
                raise ValidationError(msg)
            return None
        tag = value.get(self.tag_key)
        if tag is None:
            msg = f'Union: missing tag {self.tag_key!r} in envelope'
            raise ValidationError(msg, path=(self.tag_key,))
        variant_cls = self.variants.get(tag)
        if variant_cls is None:
            if self.fallback is not None:
                # Graceful schema evolution — unknown tag falls through
                # to the configured fallback variant.
                variant_cls = self.fallback
            else:
                msg = f'Union: unknown tag {tag!r}; expected one of {sorted(self.variants)}'
                raise ValidationError(msg, path=(self.tag_key,))
        if self.payload_key is None:
            # Flat: the variant's keys sit beside the tag in the parent's own
            # dict, so its errors already carry the right path.
            payload = {k: v for k, v in value.items() if k != self.tag_key}
            # The variant's own load, behind no ``unknown=``: the payload holds
            # the parent's keys too, and an outer refusing load has already
            # walked it (``seared._core.unknown``).
            return variant_cls.__seared_load__(payload, kwargs.get('format', 'json'))
        # A ``null`` payload is an absent one, as a ``null`` is for any key that
        # isn't nullable: the variant loads from its defaults.
        payload = value.get(self.payload_key)
        if payload is None:
            payload = {}
        try:
            return variant_cls.__seared_load__(payload, kwargs.get('format', 'json'))
        except ValidationError as e:
            add_location(e, self.payload_key)
            raise
