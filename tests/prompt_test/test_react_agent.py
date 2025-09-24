"""Tests for ReactAgent with custom prompt files."""

import os
import tempfile

from tinyagent import ReactAgent
from tinyagent.tools import tool


@tool
def simple_test_tool(x: int) -> int:
    """Simple test tool that returns x + 1."""
    return x + 1


class TestReactAgentWithPromptFile:
    """Test ReactAgent integration with prompt files."""

    def test_react_agent_with_custom_prompt_file(self):
        """Test ReactAgent initialization with custom prompt file."""
        # Create a custom prompt file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("CUSTOM PROMPT: You are a specialized assistant.\nAvailable tools:\n{tools}")
            temp_file = f.name

        try:
            # Create agent with custom prompt file
            agent = ReactAgent(
                tools=[simple_test_tool],
                prompt_file=temp_file,
                model="gpt-4o-mini",
                api_key="test-key",  # Use test key to avoid API calls
            )

            # Check that the custom prompt was loaded
            assert "CUSTOM PROMPT:" in agent._system_prompt
            assert "specialized assistant" in agent._system_prompt
            assert "simple_test_tool" in agent._system_prompt
        finally:
            os.unlink(temp_file)

    def test_react_agent_with_missing_prompt_file(self):
        """Test ReactAgent with missing prompt file - should fallback."""
        # Create agent with missing prompt file
        agent = ReactAgent(
            tools=[simple_test_tool],
            prompt_file="nonexistent_file.txt",
            model="gpt-4o-mini",
            api_key="test-key",
        )

        # Should fallback to default prompt
        assert "I'm going to tip $100K" in agent._system_prompt
        assert "simple_test_tool" in agent._system_prompt

    def test_react_agent_with_invalid_prompt_file(self):
        """Test ReactAgent with invalid prompt file - should fallback."""
        # Create an invalid file (binary)
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write(b"\xff\xfe\x00\x41")  # Invalid UTF-8
            temp_file = f.name

        try:
            # Create agent with invalid prompt file
            agent = ReactAgent(
                tools=[simple_test_tool],
                prompt_file=temp_file,
                model="gpt-4o-mini",
                api_key="test-key",
            )

            # Should fallback to default prompt
            assert "I'm going to tip $100K" in agent._system_prompt
            assert "simple_test_tool" in agent._system_prompt
        finally:
            os.unlink(temp_file)

    def test_react_agent_without_prompt_file(self):
        """Test ReactAgent without prompt file - should use default."""
        # Create agent without prompt file
        agent = ReactAgent(tools=[simple_test_tool], model="gpt-4o-mini", api_key="test-key")

        # Should use default prompt
        assert "I'm going to tip $100K" in agent._system_prompt
        assert "simple_test_tool" in agent._system_prompt

    def test_react_agent_with_empty_prompt_file(self):
        """Test ReactAgent with empty prompt file - should work."""
        # Create an empty prompt file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            # Create agent with empty prompt file
            agent = ReactAgent(
                tools=[simple_test_tool],
                prompt_file=temp_file,
                model="gpt-4o-mini",
                api_key="test-key",
            )

            # Should work with empty prompt (format will be applied)
            assert agent._system_prompt is not None
            assert "simple_test_tool" in agent._system_prompt
        finally:
            os.unlink(temp_file)

    def test_react_agent_with_markdown_prompt_file(self):
        """Test ReactAgent with markdown prompt file."""
        # Create a markdown prompt file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "# Custom System Prompt\n\nYou are a markdown-based assistant.\n\n## Tools\n{tools}"
            )
            temp_file = f.name

        try:
            # Create agent with markdown prompt file
            agent = ReactAgent(
                tools=[simple_test_tool],
                prompt_file=temp_file,
                model="gpt-4o-mini",
                api_key="test-key",
            )

            # Check that the markdown prompt was loaded
            assert "# Custom System Prompt" in agent._system_prompt
            assert "markdown-based assistant" in agent._system_prompt
            assert "simple_test_tool" in agent._system_prompt
        finally:
            os.unlink(temp_file)

    def test_react_agent_prompt_file_none_parameter(self):
        """Test ReactAgent with None prompt_file parameter."""
        # Create agent with None prompt file
        agent = ReactAgent(
            tools=[simple_test_tool], prompt_file=None, model="gpt-4o-mini", api_key="test-key"
        )

        # Should use default prompt
        assert "I'm going to tip $100K" in agent._system_prompt
        assert "simple_test_tool" in agent._system_prompt
