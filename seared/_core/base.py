from __future__ import annotations

import json
import os
from typing import Any, ClassVar, Iterable, Self, Tuple, Union


class Seared:
    __seared_fields__: ClassVar[Tuple[Tuple[str, str, Any], ...]] = ()

    @classmethod
    def dump(cls, obj: 'Seared') -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def dumps(cls, obj: 'Seared') -> str:
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
    def to_json(cls, obj: 'Seared', **kwargs: Any) -> str:
        raise NotImplementedError

    @classmethod
    def from_json(cls, source: Union[str, os.PathLike]) -> Self:
        raise NotImplementedError

    @classmethod
    def to_toml(cls, obj: 'Seared') -> str:
        raise NotImplementedError

    @classmethod
    def from_toml(cls, source: Union[str, os.PathLike]) -> Self:
        raise NotImplementedError

    @classmethod
    def to_yaml(cls, obj: 'Seared') -> str:
        raise NotImplementedError

    @classmethod
    def from_yaml(cls, source: Union[str, os.PathLike]) -> Self:
        raise NotImplementedError

    @classmethod
    def to_csv(cls, items: Iterable['Seared']) -> str:
        raise NotImplementedError

    @classmethod
    def from_csv(cls, source: Union[str, os.PathLike]) -> list[Self]:
        raise NotImplementedError
