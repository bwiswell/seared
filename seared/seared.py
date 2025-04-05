from dataclasses import fields
import typing as t

from marshmallow import Schema, post_load
from marshmallow.fields import Field as MField

from .field import Field


T = t.TypeVar('T', bound=(object,))
SchemaType = t.Type[Schema]


def schema (cls: t.Type[T]) -> t.Type[T]:
    props: t.Dict[str, MField] = {}
    for field in fields(cls):
        if isinstance(field, Field):
            props[field.name] = field.to_field(field.name)

    class BaseSchema(Schema):
        @post_load
        def make_data_class(
                    self, 
                    data: t.Mapping[str, object], 
                    **_: object
                ) -> object:
            return cls(**data)

    cls_schema = type(
        f'{cls.__name__}Schema',
        (BaseSchema,),
        props
    )

    return t.cast(SchemaType, cls_schema)