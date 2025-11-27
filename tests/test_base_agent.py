"""
Tests for BaseAgent abstract class and inheritance.
"""

import pytest

from tinyagent import tool
from tinyagent.agents.base import BaseAgent
from tinyagent.agents.code import TinyCodeAgent
from tinyagent.agents.react import ReactAgent


class TestBaseAgent:
    """Test BaseAgent abstract class functionality."""

    def test_cannot_instantiate_base_agent(self):
        """BaseAgent should not be instantiable directly."""
        with pytest.raises(ValueError, match="BaseAgent requires at least one tool"):
            BaseAgent(tools=[])

    def test_base_agent_inheritance(self):
        """Verify both agents inherit BaseAgent tool mapping."""

        @tool
        def simple_tool(x: int) -> int:
            return x * 2

        # Test ReactAgent with mock API key
        react = ReactAgent(tools=[simple_tool], api_key="test-key")
        assert isinstance(react, BaseAgent)
        assert hasattr(react, "_tool_map")
        assert "simple_tool" in react._tool_map

        # Test TinyCodeAgent with mock API key
        tiny = TinyCodeAgent(tools=[simple_tool], api_key="test-key")
        assert isinstance(tiny, BaseAgent)
        assert hasattr(tiny, "_tool_map")
        assert "simple_tool" in tiny._tool_map

    def test_duplicate_tool_name_error(self):
        """BaseAgent should fail loudly when duplicate tool names are detected."""

        @tool
        def tool_one(x: int) -> int:
            return x + 1

        @tool
        def tool_two(x: int) -> int:
            return x + 2

        # Create tools with the same name by manually modifying the name
        # This simulates the collision scenario
        from tinyagent.core.registry import Tool

        tool_a = Tool(
            fn=tool_one.fn,
            name="duplicate_name",  # Same name as tool_b
            doc=tool_one.doc,
            signature=tool_one.signature,
            is_async=False,
        )

        tool_b = Tool(
            fn=tool_two.fn,
            name="duplicate_name",  # Same name as tool_a
            doc=tool_two.doc,
            signature=tool_two.signature,
            is_async=False,
        )

        # Test with ReactAgent
        with pytest.raises(
            ValueError,
            match=r"Duplicate tool name 'duplicate_name' detected\. "
            r"Existing tool: tool_one, conflicting tool: tool_two\. "
            r"Each tool must have a unique name\.",
        ):
            ReactAgent(tools=[tool_a, tool_b], api_key="test-key")

        # Test with TinyCodeAgent
        with pytest.raises(
            ValueError,
            match=r"Duplicate tool name 'duplicate_name' detected\. "
            r"Existing tool: tool_one, conflicting tool: tool_two\. "
            r"Each tool must have a unique name\.",
        ):
            TinyCodeAgent(tools=[tool_a, tool_b], api_key="test-key")
