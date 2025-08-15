"""
Tests for tinyagent.agent.ReactAgent
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from dotenv import load_dotenv

from tinyagent import ReactAgent, tool
from tinyagent.agent import StepLimitReached
from tinyagent.tools import Tool

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")


class TestReactAgent:
    """Test suite for ReactAgent class."""

    def setup_method(self):
        """Setup test fixtures."""
        # Clear any existing tools from registry
        from tinyagent.tools import REGISTRY

        REGISTRY._data.clear()
        REGISTRY._frozen = False

        # Create test tools
        @tool
        def test_add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        @tool
        def test_multiply(x: float, y: float) -> float:
            """Multiply two numbers."""
            return x * y

        self.test_add = test_add
        self.test_multiply = test_multiply

    def teardown_method(self):
        """Clean up after tests."""
        # Clear registry
        from tinyagent.tools import REGISTRY

        REGISTRY._data.clear()
        REGISTRY._frozen = False

    # Test 1: ReactAgent initialization
    def test_agent_initialization_with_no_tools_raises_error(self):
        """Test that ReactAgent raises ValueError when initialized with no tools."""
        with pytest.raises(ValueError, match="ReactAgent requires at least one tool"):
            ReactAgent(tools=[])

    def test_agent_initialization_with_function_tools(self):
        """Test ReactAgent initialization with function tools decorated with @tool."""
        agent = ReactAgent(tools=[self.test_add, self.test_multiply])

        # Check that tools were properly registered
        assert len(agent._tool_map) == 2
        assert "test_add" in agent._tool_map
        assert "test_multiply" in agent._tool_map

        # Check tool types
        assert isinstance(agent._tool_map["test_add"], Tool)
        assert isinstance(agent._tool_map["test_multiply"], Tool)

    def test_agent_initialization_with_tool_objects(self):
        """Test ReactAgent initialization with Tool objects directly."""
        from tinyagent.tools import get_registry

        # Get Tool objects from registry
        registry = get_registry()
        tool_add = registry["test_add"]
        tool_multiply = registry["test_multiply"]

        agent = ReactAgent(tools=[tool_add, tool_multiply])

        assert len(agent._tool_map) == 2
        assert agent._tool_map["test_add"] == tool_add
        assert agent._tool_map["test_multiply"] == tool_multiply

    def test_agent_initialization_with_invalid_tool_raises_error(self):
        """Test that invalid tools raise ValueError."""

        def undecorated_function():
            pass

        with pytest.raises(ValueError, match="Invalid tool"):
            ReactAgent(tools=[undecorated_function])

    def test_agent_initialization_with_mixed_tools(self):
        """Test ReactAgent with both Tool objects and functions."""
        from tinyagent.tools import get_registry

        registry = get_registry()
        tool_add = registry["test_add"]

        agent = ReactAgent(tools=[tool_add, self.test_multiply])

        assert len(agent._tool_map) == 2
        assert "test_add" in agent._tool_map
        assert "test_multiply" in agent._tool_map

    # Test 2: API key configuration
    def test_agent_uses_provided_api_key(self):
        """Test that agent uses explicitly provided API key."""
        with patch.dict(os.environ, {}, clear=True):
            agent = ReactAgent(tools=[self.test_add], api_key="test-api-key")
            assert agent.client.api_key == "test-api-key"

    def test_agent_uses_env_api_key(self):
        """Test that agent falls back to environment variable for API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-api-key"}):
            agent = ReactAgent(tools=[self.test_add])
            assert agent.client.api_key == "env-api-key"

    def test_agent_uses_base_url_from_env(self):
        """Test that agent uses base URL from environment."""
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "https://custom.api/v1"}):
            agent = ReactAgent(tools=[self.test_add])
            assert agent.client.base_url == "https://custom.api/v1/"

    # Test 3: System prompt generation
    def test_system_prompt_generation(self):
        """Test that system prompt is correctly generated with tool descriptions."""
        agent = ReactAgent(tools=[self.test_add, self.test_multiply])

        assert "test_add: Add two numbers." in agent._system_prompt
        assert "test_multiply: Multiply two numbers." in agent._system_prompt
        assert "args=" in agent._system_prompt

    # Test 4: JSON parsing
    def test_try_parse_json_valid(self):
        """Test JSON parsing with valid JSON."""
        result = ReactAgent._try_parse_json('{"tool": "test", "arguments": {}}')
        assert result == {"tool": "test", "arguments": {}}

    def test_try_parse_json_invalid(self):
        """Test JSON parsing with invalid JSON."""
        result = ReactAgent._try_parse_json("not valid json")
        assert result is None

    # Test 5: Safe tool execution
    def test_safe_tool_execution_success(self):
        """Test successful tool execution."""
        agent = ReactAgent(tools=[self.test_add])
        ok, result = agent._safe_tool("test_add", {"a": 5, "b": 3})
        assert ok is True
        assert result == "8"

    def test_safe_tool_execution_error(self):
        """Test tool execution with error handling."""
        agent = ReactAgent(tools=[self.test_add])
        # Missing required argument
        ok, result = agent._safe_tool("test_add", {"a": 5})
        assert ok is False
        assert "ArgError:" in result

    # Test 6: Run method with mocked LLM
    @patch("tinyagent.agent.OpenAI")
    def test_run_with_direct_answer(self, mock_openai_class):
        """Test run method when LLM provides direct answer."""
        # Setup mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"answer": "42"}'))]
        mock_client.chat.completions.create.return_value = mock_response

        agent = ReactAgent(tools=[self.test_add])
        result = agent.run("What is the answer?")

        assert result == "42"
        assert mock_client.chat.completions.create.call_count == 1

    @patch("tinyagent.agent.OpenAI")
    def test_run_with_tool_call(self, mock_openai_class):
        """Test run method with tool invocation."""
        # Setup mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # First response: tool call
        mock_response1 = Mock()
        mock_response1.choices = [
            Mock(message=Mock(content='{"tool": "test_add", "arguments": {"a": 5, "b": 3}}'))
        ]

        # Second response: final answer
        mock_response2 = Mock()
        mock_response2.choices = [Mock(message=Mock(content='{"answer": "The sum is 8"}'))]

        mock_client.chat.completions.create.side_effect = [mock_response1, mock_response2]

        agent = ReactAgent(tools=[self.test_add])
        result = agent.run("What is 5 + 3?")

        assert result == "The sum is 8"
        assert mock_client.chat.completions.create.call_count == 2

    @patch("tinyagent.agent.OpenAI")
    def test_run_with_invalid_json_retry(self, mock_openai_class):
        """Test run method handling invalid JSON with retry."""
        # Setup mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # First response: invalid JSON
        mock_response1 = Mock()
        mock_response1.choices = [Mock(message=Mock(content="not valid json"))]

        # Second response: valid answer
        mock_response2 = Mock()
        mock_response2.choices = [Mock(message=Mock(content='{"answer": "42"}'))]

        mock_client.chat.completions.create.side_effect = [mock_response1, mock_response2]

        agent = ReactAgent(tools=[self.test_add])
        result = agent.run("What is the answer?")

        assert result == "42"
        assert mock_client.chat.completions.create.call_count == 2

        # Check that temperature increased
        first_call = mock_client.chat.completions.create.call_args_list[0]
        second_call = mock_client.chat.completions.create.call_args_list[1]
        assert first_call.kwargs["temperature"] == 0.0
        assert second_call.kwargs["temperature"] == 0.2

    @patch("tinyagent.agent.OpenAI")
    def test_run_with_unknown_tool(self, mock_openai_class):
        """Test run method with unknown tool name."""
        # Setup mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content='{"tool": "unknown_tool", "arguments": {}}'))
        ]

        mock_client.chat.completions.create.return_value = mock_response

        agent = ReactAgent(tools=[self.test_add])
        result = agent.run("Use unknown tool")

        assert result == "Unknown tool 'unknown_tool'."

    @patch("tinyagent.agent.OpenAI")
    def test_run_exceeds_max_steps(self, mock_openai_class):
        """Test that StepLimitReached is raised when max steps exceeded."""
        # Setup mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Always return a tool call (never an answer)
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content='{"tool": "test_add", "arguments": {"a": 1, "b": 1}}'))
        ]

        mock_client.chat.completions.create.return_value = mock_response

        agent = ReactAgent(tools=[self.test_add])

        with pytest.raises(StepLimitReached, match="Exceeded max steps"):
            agent.run("Keep calculating", max_steps=3)

        # Should have made 4 calls (3 steps + 1 final attempt)
        assert mock_client.chat.completions.create.call_count == 4

    # Test 7: Model configuration
    def test_custom_model_configuration(self):
        """Test agent with custom model configuration."""
        agent = ReactAgent(tools=[self.test_add], model="gpt-4")
        assert agent.model == "gpt-4"

    def test_default_model_configuration(self):
        """Test agent uses default model."""
        agent = ReactAgent(tools=[self.test_add])
        assert agent.model == "gpt-4o-mini"

    # Test 8: Integration test
    @patch("tinyagent.agent.OpenAI")
    def test_integration_multiple_tool_calls(self, mock_openai_class):
        """Test complex interaction with multiple tool calls."""
        # Setup mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        responses = [
            # First: multiply 3 * 4
            Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content='{"tool": "test_multiply", "arguments": {"x": 3, "y": 4}}'
                        )
                    )
                ]
            ),
            # Second: add result (12) + 8
            Mock(
                choices=[
                    Mock(
                        message=Mock(content='{"tool": "test_add", "arguments": {"a": 12, "b": 8}}')
                    )
                ]
            ),
            # Third: final answer
            Mock(choices=[Mock(message=Mock(content='{"answer": "The result is 20"}'))]),
        ]

        mock_client.chat.completions.create.side_effect = responses

        agent = ReactAgent(tools=[self.test_add, self.test_multiply])
        result = agent.run("What is 3 * 4 + 8?")

        assert result == "The result is 20"
        assert mock_client.chat.completions.create.call_count == 3
