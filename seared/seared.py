from dataclasses import dataclass, fields
from typing import Type, TypeVar, cast

from marshmallow import Schema, post_load
from marshmallow.fields import Field as MField

from .field import Field


class Seared:
    SCHEMA: Schema

    @property
    def schema (self) -> Schema:
        raise NotImplementedError
    

SchemaType = Type[Schema]
T = TypeVar('T', bound=Seared)

def seared (cls: Type[T]) -> Type[T]:
    cls = dataclass(cls)
    props: dict[str, MField] = {}
    for field in fields(cls):
        if isinstance(field, Field):
            props[field.name] = field.to_field(field.name)

    class BaseSchema(Schema):
        @post_load
        def make_data_class(
                    self, 
                    data: dict[str, object], 
                    **_: object
                ) -> object:
            return cls(**data)

    cls_schema = type(
        f'{cls.__name__}Schema',
        (BaseSchema,),
        props
    )

    schema = cast(SchemaType, cls_schema)()
    cls.SCHEMA = schema
    cls.schema = lambda _: schema
    
    return cls