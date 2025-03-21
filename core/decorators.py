"""
Decorator functions for the tinyAgent framework.

This module provides decorators used throughout the tinyAgent framework,
particularly the `tool` decorator for transforming functions into Tool instances.
"""

import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast, overload

from .tool import Tool, ParamType


# Type variables for better type annotations
F = TypeVar('F', bound=Callable[..., Any])  # Function type
T = TypeVar('T')  # Generic return type


@overload
def tool(func: F) -> F:
    """Tool decorator usage without arguments."""
    ...


@overload
def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    rate_limit: Optional[int] = None,
    retry_limit: Optional[int] = None
) -> Callable[[F], F]:
    """Tool decorator usage with arguments."""
    ...


def tool(
    name=None,
    description=None,
    rate_limit=None,
    retry_limit=None
):
    """
    Decorator to transform a function into a tool with optional rate limiting.
    
    This decorator provides a more intuitive and developer-friendly way to define tools.
    Simply decorating a function transforms it into a registered tool.
    
    Args:
        name: Optional name for the tool (defaults to function name)
        description: Optional description for the tool (defaults to function docstring)
        rate_limit: Optional rate limit for the tool (max number of calls allowed)
        retry_limit: Optional retry limit for the tool (max retries on failure)
        
    Returns:
        The decorated function wrapped as a tool with rate limiting
        
    Example:
        @tool
        def calculate_sum(a: int, b: int) -> int:
            '''Calculate the sum of two integers.'''
            return a + b
        
        @tool(rate_limit=5)
        def rate_limited_api(query: str) -> str:
            '''Make an API call with max 5 calls per session.'''
            return make_api_call(query)
    """
    # Handle case where decorator is used without parentheses
    if callable(name):
        func = name
        name = None
        return _create_tool_wrapper(func, None, None, None, None)
    
    # Handle case where decorator is used with parameters
    def decorator(func):
        return _create_tool_wrapper(func, name, description, rate_limit, retry_limit)
    
    return decorator


def _create_tool_wrapper(
    func: F, 
    name: Optional[str], 
    description: Optional[str], 
    rate_limit: Optional[int], 
    retry_limit: Optional[int]
) -> F:
    """
    Internal function to create a tool wrapper for a given function.
    
    Args:
        func: The function to wrap as a tool
        name: Optional name for the tool
        description: Optional description for the tool
        rate_limit: Optional rate limit for the tool
        retry_limit: Optional retry limit for the tool
        
    Returns:
        The wrapped function
    """
    # Get function signature and metadata
    sig = inspect.signature(func)
    
    # Set tool name and description
    tool_name = name or func.__name__.lower()
    tool_description = description or func.__doc__ or f"Tool for {func.__name__}"
    
    # If rate limit specified, add it to description
    if rate_limit is not None:
        tool_description = f"{tool_description} (Limited to {rate_limit} calls per session)"
    
    # Convert Python type hints to ParamType
    parameters = {}
    for param_name, param in sig.parameters.items():
        if param_name in ('self', 'cls'):
            continue
            
        # Map Python types to ParamType
        if param.annotation == int:
            param_type = ParamType.INTEGER
        elif param.annotation == float:
            param_type = ParamType.FLOAT
        elif param.annotation == str:
            param_type = ParamType.STRING
        else:
            param_type = ParamType.ANY
            
        parameters[param_name] = param_type
    
    # Create tool instance with rate limiting
    tool_instance = Tool(
        name=tool_name,
        description=tool_description,
        parameters=parameters,
        func=func,
        rate_limit=rate_limit
    )
    
    # Add retry limit if specified
    if retry_limit is not None:
        tool_instance.retry_limit = retry_limit
    
    # Add the tool instance as an attribute to the function
    func._tool = tool_instance
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Convert positional arguments to keyword arguments if needed
        if args and len(args) > 0:
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            # Skip self/cls if this is a method
            if param_names and param_names[0] in ('self', 'cls') and len(args) > 0:
                kwargs[param_names[1]] = args[0]
                for i, arg in enumerate(args[1:], start=2):
                    if i < len(param_names):
                        kwargs[param_names[i]] = arg
            else:
                # Not a method
                for i, arg in enumerate(args):
                    if i < len(param_names):
                        kwargs[param_names[i]] = arg
        
        # Use the tool instance directly to ensure rate limiting is applied
        return tool_instance(**kwargs)
        
    wrapper._tool = tool_instance
    
    return cast(F, wrapper)
