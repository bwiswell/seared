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

import seared as s

class MyEnum(Enum):
    A = 0
    B = 1
    C = 2

@s.seared
class MyDataclass(s.Seared):
    a: int = s.Int('a', 5)
    b: float = s.Float('b', 3.14)
    c: str = s.Str('c', 'hello')
    d: MyEnum = s.Enum('d', MyEnum, MyEnum.B)
```