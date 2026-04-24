from dataclasses import dataclass
from enum import Enum as PEnum
from typing import Optional, TypeVar, Union

from marshmallow import missing
from marshmallow.fields import Field as MField

from .field import Field


ET = TypeVar('ET', bound=PEnum)


@dataclass(frozen=True)
class EnumMeta:
    enum: ET
    missing: Optional[ET] = None


@dataclass(frozen=True)
class Enum(Field, EnumMeta):

    def to_field (self, name: str) -> MField:
        enum = self.enum
        sample_value = next(iter(enum)).value
        is_int_enum = (
            isinstance(sample_value, int) and not isinstance(sample_value, bool)
        )

        class EnumField(MField):
            def _serialize (self, value, attr, obj, **kwargs):
                if value is None: return None
                return value.value

            def _deserialize (self, value, attr, data, **kwargs):
                if is_int_enum:
                    return enum(int(value))
                return enum(value)

        return self.wrap(
            EnumField,
            data_key = self.data_key if self.data_key else name,
            load_only = not self.dump,
            load_default = self._load_default(missing)
        )
