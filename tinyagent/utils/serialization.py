"""
Serialization utilities for the tinyAgent framework.

This module provides utilities to convert complex objects to serializable formats
for JSON encoding, storage, and network transmission. It handles common Python
types as well as tinyAgent-specific objects like Tool instances.
"""

import json
from typing import Dict, Any, Callable, Optional, List, Union, Set, Type, TypeVar, cast

from ..tool import Tool, ParamType

# Define a generic type variable for type hints
T = TypeVar('T')


def tool_to_dict(tool: Tool) -> Dict[str, Any]:
    """
    Convert a Tool object to a serializable dictionary.
    
    Args:
        tool: Tool object to convert
        
    Returns:
        Dictionary representation of the tool
    """
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": {k: str(v) for k, v in tool.parameters.items()},
        "rate_limit": tool.rate_limit
    }


def convert_to_serializable(obj: Any) -> Any:
    """
    Convert any object to a JSON-serializable format.
    
    This function recursively converts any Python object to a format that can be
    safely serialized to JSON. It handles basic types, collections, custom objects,
    and special tinyAgent types.
    
    Args:
        obj: Any Python object
        
    Returns:
        JSON-serializable version of the object
        
    Examples:
        >>> convert_to_serializable({"key": Tool(...)})
        {'key': {'name': '...', 'description': '...', ...}}
        
        >>> convert_to_serializable([1, 2, set([3, 4])])
        [1, 2, [3, 4]]
    """
    # Handle None
    if obj is None:
        return None
        
    # Handle basic types that are already serializable
    if isinstance(obj, (str, int, float, bool)):
        return obj
        
    # Handle lists and tuples
    if isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
        
    # Handle dictionaries
    if isinstance(obj, dict):
        return {
            str(convert_to_serializable(k)): convert_to_serializable(v) 
            for k, v in obj.items()
        }
        
    # Handle Tool objects
    if isinstance(obj, Tool):
        return tool_to_dict(obj)
        
    # Handle ParamType enum
    if isinstance(obj, ParamType):
        return str(obj)
        
    # Handle callables (functions, methods, etc.)
    if callable(obj):
        if hasattr(obj, '__name__'):
            return f"<function {obj.__name__}>"
        else:
            return "<function>"
    
    # Handle sets
    if isinstance(obj, set):
        return list(obj)
        
    # Handle objects with __dict__ attribute
    if hasattr(obj, '__dict__'):
        return {
            k: convert_to_serializable(v) 
            for k, v in obj.__dict__.items() 
            if not k.startswith('_')  # Skip private attributes
        }
    
    # Fallback: convert to string
    return str(obj)


def to_serializable_dict(obj: Any) -> Dict[str, Any]:
    """
    Convert any object to a serializable dictionary.
    
    This function is a wrapper around convert_to_serializable that ensures
    the result is a dictionary. If the input is not already a dictionary,
    it will be wrapped in one.
    
    Args:
        obj: Any Python object
        
    Returns:
        Dictionary with serializable values
        
    Examples:
        >>> to_serializable_dict({"a": 1, "b": [2, 3]})
        {'a': 1, 'b': [2, 3]}
        
        >>> to_serializable_dict("hello")
        {'value': 'hello'}
    """
    if isinstance(obj, dict):
        return cast(Dict[str, Any], convert_to_serializable(obj))
    elif hasattr(obj, '__dict__'):
        return cast(Dict[str, Any], convert_to_serializable(obj.__dict__))
    else:
        return {"value": convert_to_serializable(obj)}


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """
    Safely convert any object to a JSON string.
    
    This function first converts the object to a serializable format
    and then serializes it to a JSON string. It handles any Python object,
    including those that are not normally JSON-serializable.
    
    Args:
        obj: Object to serialize
        **kwargs: Additional arguments to pass to json.dumps
        
    Returns:
        JSON string representation of the object
        
    Examples:
        >>> safe_json_dumps({"key": object()})
        '{"key": "<object object at ...>"}'
        
        >>> safe_json_dumps([1, 2, 3], indent=2)
        '[\n  1,\n  2,\n  3\n]'
    """
    return json.dumps(convert_to_serializable(obj), **kwargs)


def safe_json_loads(json_str: str, object_hook: Optional[Callable[[Dict[str, Any]], Any]] = None) -> Any:
    """
    Safely parse a JSON string to a Python object.
    
    This function provides a wrapper around json.loads with better error
    handling and optional object hook for custom deserialization.
    
    Args:
        json_str: JSON string to parse
        object_hook: Optional function to transform objects during deserialization
        
    Returns:
        Deserialized Python object
        
    Raises:
        ValueError: If the JSON string is invalid
        
    Examples:
        >>> safe_json_loads('{"name": "tool", "value": 42}')
        {'name': 'tool', 'value': 42}
    """
    try:
        return json.loads(json_str, object_hook=object_hook)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON string: {e}")
