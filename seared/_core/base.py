from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar, Self

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable


class Seared:
    __seared_fields__: ClassVar[tuple[tuple[str, str, Any], ...]] = ()

    @classmethod
    def dump(cls, obj: Seared) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def dumps(cls, obj: Seared) -> str:
        return json.dumps(cls.dump(obj))

    @classmethod
    def load(cls, data: dict[str, Any]) -> Self:
        raise NotImplementedError

    @classmethod
    def loads(cls, data: str) -> Self:
        return cls.load(json.loads(data))

    # Per-format codecs. Real implementations are attached at decorator
    # time (``seared/formats/_attach_format_methods``); these
    # declarations exist so the methods type-check on the base surface,
    # exactly like ``dump`` / ``load`` above.

    @classmethod
    def to_json(cls, obj: Seared, **kwargs: Any) -> str:
        raise NotImplementedError

    @classmethod
    def from_json(cls, source: str | os.PathLike) -> Self:
        raise NotImplementedError

    @classmethod
    def to_toml(cls, obj: Seared) -> str:
        raise NotImplementedError

    @classmethod
    def from_toml(cls, source: str | os.PathLike) -> Self:
        raise NotImplementedError

    @classmethod
    def to_yaml(cls, obj: Seared) -> str:
        raise NotImplementedError

    @classmethod
    def from_yaml(cls, source: str | os.PathLike) -> Self:
        raise NotImplementedError

    @classmethod
    def to_csv(cls, items: Iterable[Seared]) -> str:
        raise NotImplementedError

    @classmethod
    def from_csv(cls, source: str | os.PathLike) -> list[Self]:
        raise NotImplementedError
