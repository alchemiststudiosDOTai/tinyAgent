"""Tests for TinyCodeAgent with custom prompt files."""

import os
import tempfile
from collections.abc import Iterator

import pytest

from tinyagent import tool
from tinyagent.agents import TinyCodeAgent
from tinyagent.core.registry import REGISTRY


@tool
def calculator_tool(expression: str) -> float:
    """Simple calculator tool."""
    return eval(expression)  # Note: eval is dangerous but acceptable for testing


@pytest.fixture(autouse=True)
def _ensure_calculator_tool_registered() -> Iterator[None]:
    """Ensure the calculator tool is present in the registry for each test."""
    original_frozen = REGISTRY._frozen
    original_data = dict(REGISTRY._data)

    if not isinstance(REGISTRY._data, dict):
        REGISTRY._data = dict(REGISTRY._data)
    REGISTRY._frozen = False
    REGISTRY.register(calculator_tool)

    yield

    REGISTRY._data = original_data
    if original_frozen:
        REGISTRY._frozen = False
        REGISTRY.freeze()
    else:
        REGISTRY._frozen = False


class TestTinyCodeAgentWithPromptFile:
    """Test TinyCodeAgent integration with prompt files."""

    def test_code_agent_with_custom_prompt_file(self):
        """Test TinyCodeAgent initialization with custom prompt file."""
        # Create a custom prompt file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                "CUSTOM CODE PROMPT: You are a specialized Python executor.\nAvailable helpers: {helpers}"
            )
            temp_file = f.name

        try:
            # Create agent with custom prompt file
            agent = TinyCodeAgent(
                tools=[calculator_tool],
                prompt_file=temp_file,
                model="gpt-4o-mini",
                api_key="test-key",  # Use test key to avoid API calls
            )

            # Check that the custom prompt was loaded
            assert "CUSTOM CODE PROMPT:" in agent._system_prompt
            assert "specialized Python executor" in agent._system_prompt
            assert "calculator_tool" in agent._system_prompt
        finally:
            os.unlink(temp_file)

    def test_code_agent_with_missing_prompt_file(self):
        """Test TinyCodeAgent with missing prompt file - should fallback."""
        # Create agent with missing prompt file
        agent = TinyCodeAgent(
            tools=[calculator_tool],
            prompt_file="nonexistent_file.txt",
            model="gpt-4o-mini",
            api_key="test-key",
        )

        # Should fallback to default prompt
        assert "###Role###" in agent._system_prompt
        assert "Python code execution agent" in agent._system_prompt
        assert "calculator_tool" in agent._system_prompt

    def test_code_agent_with_system_suffix_and_prompt_file(self):
        """Test TinyCodeAgent with both system_suffix and prompt_file."""
        # Create a custom prompt file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                "CUSTOM CODE PROMPT: You are a specialized Python executor.\nAvailable helpers: {helpers}"
            )
            temp_file = f.name

        try:
            # Create agent with both custom prompt file and system suffix
            agent = TinyCodeAgent(
                tools=[calculator_tool],
                prompt_file=temp_file,
                system_suffix="Additional instructions for testing.",
                model="gpt-4o-mini",
                api_key="test-key",
            )

            # Check that both custom prompt and suffix are applied
            assert "CUSTOM CODE PROMPT:" in agent._system_prompt
            assert "specialized Python executor" in agent._system_prompt
            assert "calculator_tool" in agent._system_prompt
            assert "Additional instructions for testing" in agent._system_prompt
        finally:
            os.unlink(temp_file)

    def test_code_agent_without_prompt_file(self):
        """Test TinyCodeAgent without prompt file - should use default."""
        # Create agent without prompt file
        agent = TinyCodeAgent(tools=[calculator_tool], model="gpt-4o-mini", api_key="test-key")

        # Should use default prompt
        assert "###Role###" in agent._system_prompt
        assert "Python code execution agent" in agent._system_prompt
        assert "calculator_tool" in agent._system_prompt

    def test_code_agent_with_empty_prompt_file(self):
        """Test TinyCodeAgent with empty prompt file - should work."""
        # Create an empty prompt file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            # Create agent with empty prompt file
            agent = TinyCodeAgent(
                tools=[calculator_tool],
                prompt_file=temp_file,
                model="gpt-4o-mini",
                api_key="test-key",
            )

            # Should work with empty prompt (format will be applied)
            assert agent._system_prompt is not None
            assert "calculator_tool" in agent._system_prompt
        finally:
            os.unlink(temp_file)

    def test_code_agent_with_markdown_prompt_file(self):
        """Test TinyCodeAgent with markdown prompt file."""
        # Create a markdown prompt file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "# Custom Code System Prompt\n\nYou are a markdown-based Python executor.\n\n## Helpers\n{helpers}"
            )
            temp_file = f.name

        try:
            # Create agent with markdown prompt file
            agent = TinyCodeAgent(
                tools=[calculator_tool],
                prompt_file=temp_file,
                model="gpt-4o-mini",
                api_key="test-key",
            )

            # Check that the markdown prompt was loaded
            assert "# Custom Code System Prompt" in agent._system_prompt
            assert "markdown-based Python executor" in agent._system_prompt
            assert "calculator_tool" in agent._system_prompt
        finally:
            os.unlink(temp_file)

    def test_code_agent_prompt_file_none_parameter(self):
        """Test TinyCodeAgent with None prompt_file parameter."""
        # Create agent with None prompt file
        agent = TinyCodeAgent(
            tools=[calculator_tool], prompt_file=None, model="gpt-4o-mini", api_key="test-key"
        )

        # Should use default prompt
        assert "###Role###" in agent._system_prompt
        assert "Python code execution agent" in agent._system_prompt
        assert "calculator_tool" in agent._system_prompt

    def test_code_agent_with_extra_imports_and_prompt_file(self):
        """Test TinyCodeAgent with extra_imports and prompt_file."""
        # Create a custom prompt file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                "CUSTOM CODE PROMPT: You are a specialized Python executor.\nAvailable helpers: {helpers}"
            )
            temp_file = f.name

        try:
            # Create agent with both extra_imports and custom prompt file
            agent = TinyCodeAgent(
                tools=[calculator_tool],
                prompt_file=temp_file,
                extra_imports=["math", "json"],
                model="gpt-4o-mini",
                api_key="test-key",
            )

            # Check that custom prompt was loaded and extra_imports work
            assert "CUSTOM CODE PROMPT:" in agent._system_prompt
            assert "specialized Python executor" in agent._system_prompt
            assert "calculator_tool" in agent._system_prompt
            assert "math" in agent._executor._allowed
            assert "json" in agent._executor._allowed
        finally:
            os.unlink(temp_file)
