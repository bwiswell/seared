from enum import Enum


class Color(Enum):
    RED   = 0
    GREEN = 1
    BLUE  = 2


class Status(str, Enum):
    ACTIVE   = 'active'
    INACTIVE = 'inactive'
    PENDING  = 'pending'
