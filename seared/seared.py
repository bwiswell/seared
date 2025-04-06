from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Type, TypeVar, cast

from marshmallow import Schema, post_dump, post_load, EXCLUDE
from marshmallow.fields import Field as MField

from .field import Field


class Seared:
    SCHEMA: Schema
    
    @classmethod
    def dump (cls, obj: Seared) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def load (cls, data: dict[str, Any]) -> Seared:
        raise NotImplementedError
    

SchemaType = Type[Schema]
T = TypeVar('T', bound=Seared)

def seared (cls: Type[T]) -> Type[T]:
    cls = dataclass(cls)
    props: dict[str, MField] = {}
    for field in fields(cls):
        if isinstance(field.default, Field):
            props[field.name] = field.default.to_field(field.name)

    class BaseSchema(Schema):
        @post_dump
        def remove_skip_values (
                    self,
                    data: dict[str, Any],
                    **kwargs: dict[str, Any]
                ) -> dict[str, Any]:
            return {
                k: v for k, v in data.items()
                if not v is None
            }

        @post_load
        def make_data_class(
                    self, 
                    data: dict[str, object], 
                    **kwargs: dict[str, Any]
                ) -> object:
            return cls(**data)

    cls_schema = type(
        f'{cls.__name__}Schema',
        (BaseSchema,),
        props
    )

    schema = cast(SchemaType, cls_schema)()

    cls.unknown = EXCLUDE
    cls.dump = classmethod(lambda _, obj: schema.dump(obj))
    cls.load = classmethod(lambda _, data: schema.load(data))
    cls.SCHEMA = schema
    
    return cls