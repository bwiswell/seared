from typing import Optional

from marshmallow import missing as mm_missing
from marshmallow.fields import Field as MField
from marshmallow.fields import Tuple as MTuple

from .field import Field


class Tuple(Field):

    def __init__(
        self,
        *fields: Field,
        missing: Optional[tuple] = None,
        data_key: Optional[str] = None,
        keyed: bool = False,
        many: bool = False,
        required: bool = False,
        dump: bool = True,
    ):
        object.__setattr__(self, 'tuple_fields', fields)
        object.__setattr__(self, 'missing', missing)
        object.__setattr__(self, 'data_key', data_key)
        object.__setattr__(self, 'keyed', keyed)
        object.__setattr__(self, 'many', many)
        object.__setattr__(self, 'required', required)
        object.__setattr__(self, 'dump', dump)

    def to_field(self, name: str) -> MField:
        # '_' is a positional placeholder — data_key is irrelevant on inner fields
        mfields = tuple(f.to_field('_') for f in self.tuple_fields)
        return self.wrap(
            lambda **kws: MTuple(tuple_fields=mfields, **kws),
            data_key=self.data_key if self.data_key else name,
            load_only=not self.dump,
            load_default=self._load_default(mm_missing)
        )
