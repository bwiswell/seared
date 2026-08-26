from __future__ import annotations

from typing import Any, Callable, Optional, Type

from .._core.errors import ValidationError
from .field import Field


class T(Field):
    __slots__ = ('schema',)

    def __init__(
        self,
        schema: Type[Any],
        *,
        default: Any = None,
        default_factory: Optional[Callable[[], Any]] = None,
        missing: Any = None,
        data_key: Optional[str] = None,
        keyed: bool = False,
        many: bool = False,
        required: bool = False,
        dump: bool = True,
    ):
        super().__init__(
            data_key=data_key,
            keyed=keyed,
            many=many,
            required=required,
            dump=dump,
            default=default,
            default_factory=default_factory,
            missing=missing,
        )
        object.__setattr__(self, 'schema', schema)

    def serialize(self, value, validate: bool = True, **kwargs):
        if not isinstance(value, self.schema):
            if validate:
                raise ValidationError(
                    f'expected {self.schema.__name__}, got {type(value).__name__}'
                )
        return self.schema.dump(value)

    def deserialize(self, value, validate: bool = True, **kwargs):
        if isinstance(value, self.schema):
            return value
        return self.schema.load(value)
