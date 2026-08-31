from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from seared._core.base import Seared

from seared._core.errors import ValidationError

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
    it under a wire key. Only one ``UNWRAP`` field is allowed per class.

    Unknown tags on load raise ``ValidationError`` by default. Pass
    ``default=<VariantCls>`` to enable graceful schema-evolution
    fallback: unknown tags coerce to the named default variant rather
    than raising. Useful when older consumers may receive newer
    schemas — they decode what they can recognise and route the rest
    to a generic / sentinel variant.

    A value instance whose type isn't one of the declared variants
    also raises ``ValidationError`` on serialize (strict).
    """

    variants: dict[str, type[Seared]]
    tag_key: str = 'type'
    payload_key: str | None = None
    default: type[Seared] | None = None

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
        if self.default is not None and not isinstance(self.default, type):
            msg = f'Union: default must be a class, got {self.default!r}'
            raise TypeError(msg)

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> dict:
        """Variant instance → the ``{tag, payload}`` envelope (flat or nested)."""
        for tag, variant_cls in self.variants.items():
            if isinstance(value, variant_cls):
                payload = variant_cls.dump(value)
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
            raise ValidationError(msg)
        variant_cls = self.variants.get(tag)
        if variant_cls is None:
            if self.default is not None:
                # Graceful schema evolution — unknown tag falls through
                # to the configured default variant.
                variant_cls = self.default
            else:
                msg = f'Union: unknown tag {tag!r}; expected one of {sorted(self.variants)}'
                raise ValidationError(msg)
        if self.payload_key is None:
            payload = {k: v for k, v in value.items() if k != self.tag_key}
        else:
            payload = value.get(self.payload_key, {})
        return variant_cls.load(payload)
