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
    d: MyClassA = s.Nested('d', MyClassA.SCHEMA)
    e: MyEnum = s.Enum('e', MyEnum, MyEnum.B)


data = {
    'a': 3,
    'c': 'world',
    'd': { 'a': 5 },
    'e': 1
}

# loading
my_obj = MyClassB.SCHEMA.load(data)

# dumping
MyClassB.SCHEMA.dump(my_obj, 'out.json')
```