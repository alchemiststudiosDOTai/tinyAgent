"""
tinyagent.core.schema
JSON Schema utilities for tool calling.
"""

from __future__ import annotations

import inspect
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Literal,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

if TYPE_CHECKING:
    from .registry import Tool

__all__ = ["python_type_to_json_schema", "tool_to_json_schema"]

TYPE_KEY = "type"
PROPERTIES_KEY = "properties"
REQUIRED_KEY = "required"
ENUM_KEY = "enum"
ITEMS_KEY = "items"
ANY_OF_KEY = "anyOf"
DESCRIPTION_KEY = "description"
ADDITIONAL_PROPERTIES_KEY = "additionalProperties"
DEFAULT_KEY = "default"

OBJECT_TYPE = "object"
ARRAY_TYPE = "array"
STRING_TYPE = "string"
INTEGER_TYPE = "integer"
NUMBER_TYPE = "number"
BOOLEAN_TYPE = "boolean"
NULL_TYPE = "null"

_NONE_TYPE = type(None)
_ARRAY_ORIGINS = (list, set)


def python_type_to_json_schema(python_type: Any) -> dict[str, Any]:
    """Map Python types to JSON Schema fragments."""
    if python_type in {Any, object}:
        return {TYPE_KEY: OBJECT_TYPE}

    origin = get_origin(python_type)
    args = get_args(python_type)

    if origin is not None:
        if origin is Annotated:
            return python_type_to_json_schema(args[0])
        if origin is Literal:
            return _literal_schema(args)
        if origin is Union:
            return _union_schema(args)
        if origin is dict:
            return _dict_schema(args)
        if origin is tuple:
            return _tuple_schema(args)
        if origin in _ARRAY_ORIGINS:
            return _array_schema(args)

    if python_type is str:
        return {TYPE_KEY: STRING_TYPE}
    if python_type is bool:
        return {TYPE_KEY: BOOLEAN_TYPE}
    if python_type is int:
        return {TYPE_KEY: INTEGER_TYPE}
    if python_type is float:
        return {TYPE_KEY: NUMBER_TYPE}
    if python_type is _NONE_TYPE:
        return {TYPE_KEY: NULL_TYPE}
    if inspect.isclass(python_type) and issubclass(python_type, Enum):
        return _enum_schema(python_type)

    return {TYPE_KEY: OBJECT_TYPE}


def tool_to_json_schema(tool: "Tool") -> dict[str, Any]:
    """Convert a Tool signature to a JSON Schema for its arguments."""
    signature = tool.signature
    hints = get_type_hints(tool.fn)

    properties: dict[str, Any] = {}
    required: list[str] = []
    empty_default = inspect._empty

    for name, param in signature.parameters.items():
        param_type = hints.get(name, param.annotation)
        param_schema = python_type_to_json_schema(param_type)
        if param.default is empty_default:
            required.append(name)
        else:
            param_schema[DEFAULT_KEY] = param.default
        properties[name] = param_schema

    schema: dict[str, Any] = {
        TYPE_KEY: OBJECT_TYPE,
        PROPERTIES_KEY: properties,
        ADDITIONAL_PROPERTIES_KEY: False,
    }
    if required:
        schema[REQUIRED_KEY] = required
    if tool.doc:
        schema[DESCRIPTION_KEY] = tool.doc

    return schema


def _array_schema(args: tuple[Any, ...]) -> dict[str, Any]:
    item_type = args[0] if args else Any
    items_schema = python_type_to_json_schema(item_type)
    return {TYPE_KEY: ARRAY_TYPE, ITEMS_KEY: items_schema}


def _tuple_schema(args: tuple[Any, ...]) -> dict[str, Any]:
    if not args:
        return _array_schema(())
    if len(args) == 2 and args[1] is Ellipsis:
        return _array_schema((args[0],))

    schemas = [python_type_to_json_schema(item) for item in args]
    return {TYPE_KEY: ARRAY_TYPE, ITEMS_KEY: {ANY_OF_KEY: schemas}}


def _dict_schema(args: tuple[Any, ...]) -> dict[str, Any]:
    value_type = args[1] if len(args) == 2 else Any
    value_schema = python_type_to_json_schema(value_type)
    return {TYPE_KEY: OBJECT_TYPE, ADDITIONAL_PROPERTIES_KEY: value_schema}


def _union_schema(args: tuple[Any, ...]) -> dict[str, Any]:
    schemas = [python_type_to_json_schema(item) for item in args]
    return {ANY_OF_KEY: schemas}


def _literal_schema(args: tuple[Any, ...]) -> dict[str, Any]:
    values = list(args)
    schema: dict[str, Any] = {ENUM_KEY: values}
    type_name = _literal_type_name(values)
    if type_name is not None:
        schema[TYPE_KEY] = type_name
    return schema


def _literal_type_name(values: list[Any]) -> str | None:
    if not values:
        return None

    types = {type(value) for value in values}
    if len(types) != 1:
        return None

    only_type = next(iter(types))
    return python_type_to_json_schema(only_type).get(TYPE_KEY)


def _enum_schema(enum_type: type[Enum]) -> dict[str, Any]:
    values = [member.value for member in enum_type]
    schema: dict[str, Any] = {ENUM_KEY: values}
    type_name = _literal_type_name(values)
    if type_name is not None:
        schema[TYPE_KEY] = type_name
    return schema
