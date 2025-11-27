"""
tinyagent.agents.base
BaseAgent abstract class for shared agent functionality.

This module provides the BaseAgent abstract class that eliminates
code duplication between ReactAgent and TinyCodeAgent by centralizing
tool mapping logic.

Public surface
--------------
BaseAgent  – abstract base class
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Sequence
from dataclasses import dataclass, field

from ..core.registry import Tool

__all__ = ["BaseAgent"]


@dataclass(kw_only=True)
class BaseAgent(ABC):
    """
    Abstract base class for all agent types.

    BaseAgent provides shared functionality for tool validation and mapping,
    eliminating code duplication between concrete agent implementations.

    Parameters
    ----------
    tools
        Sequence of Tool objects or @tool decorated functions
    """

    tools: Sequence[Tool]
    _tool_map: dict[str, Tool] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize shared agent state."""
        if not self.tools:
            raise ValueError(f"{self.__class__.__name__} requires at least one tool.")

        self._validate_tools()
        self._build_tool_map()

    def _validate_tools(self) -> None:
        """Validate that all tools are properly formatted."""
        # Basic validation - tools sequence is not empty (already checked above)
        # Additional validation can be added here as needed
        pass

    def _build_tool_map(self) -> None:
        """Build the internal tool map from the tools sequence."""
        self._tool_map = {}

        for item in self.tools:
            if isinstance(item, Tool):
                # Check for duplicate tool name
                if item.name in self._tool_map:
                    existing_tool = self._tool_map[item.name]
                    raise ValueError(
                        f"Duplicate tool name '{item.name}' detected. "
                        f"Existing tool: {existing_tool.fn.__name__}, "
                        f"conflicting tool: {item.fn.__name__}. "
                        f"Each tool must have a unique name."
                    )
                self._tool_map[item.name] = item
            else:
                raise ValueError(f"Invalid tool: {item}. Use @tool decorator.")
