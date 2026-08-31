from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from seared._core.errors import ValidationError

from .field import Field


class T(Field):
    __slots__ = ('schema',)

    def __init__(  # noqa: PLR0913 — mirrors the full Field option set
        self,
        schema: type[Any],
        *,
        default: Any = None,
        default_factory: Callable[[], Any] | None = None,
        missing: Any = None,
        data_key: str | None = None,
        keyed: bool = False,
        many: bool = False,
        required: bool = False,
        dump: bool = True,
        doc: str | None = None,
    ) -> None:
        """Bind the nested ``schema`` class alongside the standard field options."""
        super().__init__(
            data_key=data_key,
            keyed=keyed,
            many=many,
            required=required,
            dump=dump,
            default=default,
            default_factory=default_factory,
            missing=missing,
            doc=doc,
        )
        object.__setattr__(self, 'schema', schema)

    def serialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:
        """Nested instance → the nested schema's dumped dict."""
        if not isinstance(value, self.schema) and validate:
            msg = f'expected {self.schema.__name__}, got {type(value).__name__}'
            raise ValidationError(msg)
        return self.schema.dump(value)

    def deserialize(self, value: Any, validate: bool = True, **kwargs: Any) -> Any:  # noqa: ARG002 — signature fixed by Field
        """Dict → an instance of the nested schema."""
        if isinstance(value, self.schema):
            return value
        return self.schema.load(value)
