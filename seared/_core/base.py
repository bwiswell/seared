from __future__ import annotations

import json
from typing import Any, ClassVar, Self, Tuple


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
