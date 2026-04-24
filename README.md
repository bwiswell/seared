# seared

`seared` is a lightweight Python wrapper around `marshmallow`.

## Setup

### Using `pip`
```sh
pip install git+https://www.github.com/bwiswell/seared.git
```

### Using `uv`
```sh
uv add git+https://www.github.com/bwiswell/seared.git
```

**Note:** if the consuming project uses `hatchling` as its build backend, adding `seared` as a direct git reference may require enabling `allow-direct-references` in that project's `pyproject.toml`:
> ```toml
> [tool.hatch.metadata]
> allow-direct-references = true
> ```

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
    a: Optional[int] = s.Int(data_key='propertyA')
    b: Optional[float] = s.Float(data_key='propertyB')
    c: Optional[str] = s.Str(data_key='propertyC')

@s.seared
class MyClassB(s.Seared):
    a: int = s.Int(5)
    b: float = s.Float(3.14)
    c: str = s.Str('hello')
    d: MyClassA = s.T(MyClassA.SCHEMA, required=True)
    e: MyEnum = s.Enum(MyEnum, MyEnum.B)
    f: list[int] = s.Int([], many=True)
    g: dict[str, float] = s.Float({}, keyed=True)
    h: dict = s.Dict(required=True)


data = {
    'a': 3,
    'c': 'world',
    'd': { 'propertyA': 5 },
    'e': 2,
    'f': [3, 7, 4, 1],
    'g': { 'a': 3.5, 'b': 1.6, 'c': 7.5 },
    'h': { 'version': 2, 'tags': ['alpha', 'beta'], 'meta': { 'author': 'bw' } }
}

# loading
my_obj = MyClassB.load(data)

# dumping
out = MyClassB.dump(my_obj)

print(out)
```