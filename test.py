from enum import Enum
from typing import Optional

import seared as s

class MyEnum(Enum):
    A = 0
    B = 1
    C = 2

@s.seared
class MyClassA(s.Seared):
    a: Optional[int] = s.Int('propertyA')
    b: Optional[float] = s.Float('propertyB')
    c: Optional[str] = s.Str('propertyC')

@s.seared
class MyClassB(s.Seared):
    a: int = s.Int('a', 5)
    b: float = s.Float('b', 3.14)
    c: str = s.Str('c', 'hello')
    d: MyClassA = s.T('d', MyClassA.SCHEMA)
    e: MyEnum = s.Enum('e', MyEnum, MyEnum.B)


data = {
    'a': 3,
    'c': 'world',
    'd': { 'propertyA': 5 },
    'e': 2
}

# loading
my_obj = MyClassB.load(data)

# dumping
out = MyClassB.dump(my_obj)