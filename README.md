# seared

`seared` is a lightweight Python wrapper around `marshmallow` that simplifies the process of creating serializable `dataclass` definitions.

## Setup

### Using `pip`
```sh
pip install git+https://www.github.com/bwiswell/seared.git
```

### Using `poetry`
```sh
poetry add git+https://www.github.com/bwiswell/seared.git
```

## Usage
```python
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
    f: list[int] = s.Int('f', [], many=True)
    g: dict[str, float] = s.Float('g', {}, keyed=True)


data = {
    'a': 3,
    'c': 'world',
    'd': { 'propertyA': 5 },
    'e': 2,
    'f': [3, 7, 4, 1],
    'g': { 'a': 3.5, 'b': 1.6, 'c': 7.5 }
}

# loading
my_obj = MyClassB.load(data)

# dumping
out = MyClassB.dump(my_obj)

print(out)
```