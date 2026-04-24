from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from marshmallow import missing
from marshmallow.fields import Field as MField

from .field import Field


@dataclass(frozen=True)
class TimeDeltaMeta:
    missing: Optional[timedelta] = None


@dataclass(frozen=True)
class TimeDelta(Field, TimeDeltaMeta):

    def to_field(self, name: str) -> MField:
        class TimeDeltaField(MField):
            def _serialize(self, value, attr, obj, **kwargs):
                if value is None:
                    return None
                return value.total_seconds()

            def _deserialize(self, value, attr, data, **kwargs):
                return timedelta(seconds=float(value))

        return self.wrap(
            TimeDeltaField,
            data_key=self.data_key if self.data_key else name,
            load_only=not self.dump,
            load_default=self._load_default(missing)
        )
