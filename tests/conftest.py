from enum import Enum, StrEnum


class Color(Enum):
    RED = 0
    GREEN = 1
    BLUE = 2


class Status(StrEnum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    PENDING = 'pending'
