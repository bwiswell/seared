from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Optional, Type

from .._core.errors import ValidationError
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

    variants: Dict[str, Type]
    tag_key: str = 'type'
    payload_key: Optional[str] = None
    default: Optional[Type] = None

    UNWRAP: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if not self.variants:
            raise TypeError('Union: variants mapping must be non-empty')
        for tag, cls in self.variants.items():
            if not isinstance(tag, str) or not tag:
                raise TypeError(f'Union: tag must be a non-empty string, got {tag!r}')
            if not isinstance(cls, type):
                raise TypeError(
                    f'Union: variant for tag {tag!r} must be a class, '
                    f'got {cls!r}'
                )
        if self.default is not None and not isinstance(self.default, type):
            raise TypeError(
                f'Union: default must be a class, got {self.default!r}'
            )

    def serialize(self, value: Any, validate: bool = True, **kwargs) -> dict:
        for tag, variant_cls in self.variants.items():
            if isinstance(value, variant_cls):
                payload = variant_cls.dump(value)
                if self.payload_key is None:
                    # Flat: merge tag + payload at top level.
                    if self.tag_key in payload:
                        raise ValidationError(
                            f'Union: flat envelope collides — variant '
                            f'{variant_cls.__name__} has a field named '
                            f'{self.tag_key!r}'
                        )
                    return {self.tag_key: tag, **payload}
                return {self.tag_key: tag, self.payload_key: payload}
        if validate:
            names = [v.__name__ for v in self.variants.values()]
            raise ValidationError(
                f'Union: value of type {type(value).__name__} does not match '
                f'any declared variant ({names})'
            )
        return {}

    def deserialize(self, data: Any, validate: bool = True, **kwargs) -> Any:
        if not isinstance(data, dict):
            if validate:
                raise ValidationError(
                    f'Union: expected dict, got {type(data).__name__}'
                )
            return None
        tag = data.get(self.tag_key)
        if tag is None:
            raise ValidationError(
                f'Union: missing tag {self.tag_key!r} in envelope'
            )
        variant_cls = self.variants.get(tag)
        if variant_cls is None:
            if self.default is not None:
                # Graceful schema evolution — unknown tag falls through
                # to the configured default variant.
                variant_cls = self.default
            else:
                raise ValidationError(
                    f'Union: unknown tag {tag!r}; expected one of '
                    f'{sorted(self.variants)}'
                )
        if self.payload_key is None:
            payload = {k: v for k, v in data.items() if k != self.tag_key}
        else:
            payload = data.get(self.payload_key, {})
        return variant_cls.load(payload)
