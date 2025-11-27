"""
tinyagent.core.registry
Tool decorator with fail-fast validation.

Public surface
--------------
tool                 – decorator (returns Tool)
Tool                 – dataclass wrapper
ToolDefinitionError  – raised on invalid tool signature
"""

from __future__ import annotations

import asyncio
import inspect
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Dict, get_type_hints

__all__ = [
    "Tool",
    "tool",
    "ToolDefinitionError",
]


class ToolDefinitionError(ValueError):
    """Raised when @tool decorator finds invalid function signature."""

    pass


@dataclass(slots=True)
class Tool:
    """Wraps a callable with metadata."""

    fn: Callable[..., Any]
    name: str
    doc: str
    signature: inspect.Signature
    is_async: bool = False

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.fn(*args, **kwargs)

    async def run(self, payload: Dict[str, Any]) -> str:
        """Execute tool with async-aware execution.

        Async tools are awaited directly, sync tools run in thread pool
        to avoid blocking the event loop.
        """
        bound = self.signature.bind(**payload)
        if self.is_async:
            result = await self.fn(*bound.args, **bound.kwargs)
        else:
            # Run sync tools in thread pool to avoid blocking event loop
            result = await asyncio.to_thread(self.fn, *bound.args, **bound.kwargs)
        return str(result)


def tool(fn: Callable[..., Any]) -> Tool:
    """Decorate a function as a Tool with validation.

    Validates:
    - All parameters have type annotations
    - Return type annotation is present
    - Warns if no docstring (but does not fail)

    Parameters
    ----------
    fn
        The function to wrap as a Tool

    Returns
    -------
    Tool
        The wrapped Tool object

    Raises
    ------
    ToolDefinitionError
        If type annotations are missing
    """
    sig = inspect.signature(fn)
    hints = get_type_hints(fn)

    # Validate all parameters have type hints
    for param_name in sig.parameters:
        if param_name not in hints:
            raise ToolDefinitionError(
                f"Missing type hint for parameter '{param_name}' in {fn.__name__}"
            )

    # Validate return type exists
    if "return" not in hints:
        raise ToolDefinitionError(f"Missing return type annotation for {fn.__name__}")

    # Warn if no docstring
    if not fn.__doc__:
        warnings.warn(f"Tool '{fn.__name__}' has no docstring", stacklevel=2)

    return Tool(
        fn=fn,
        name=fn.__name__,
        doc=(fn.__doc__ or "").strip(),
        signature=sig,
        is_async=inspect.iscoroutinefunction(fn),
    )
