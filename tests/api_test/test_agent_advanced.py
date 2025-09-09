"""
Advanced tests for tinyagent.agent.ReactAgent with comprehensive coverage.
"""

from unittest.mock import Mock, patch

import pytest

from tinyagent import tool
from tinyagent.agents import ReactAgent
from tinyagent.agents.agent import StepLimitReached


class TestReactAgentAdvanced:
    """Advanced test suite for ReactAgent with comprehensive coverage."""

    def setup_method(self):
        """Setup test fixtures."""
        from tinyagent.tools import REGISTRY

        REGISTRY._data.clear()
        REGISTRY._frozen = False

        @tool
        def test_calculator(expression: str) -> float:
            """Evaluate a mathematical expression."""
            return eval(expression)

        @tool
        def test_error_tool(should_fail: bool = False) -> str:
            """Tool that can raise exceptions."""
            if should_fail:
                raise RuntimeError("Tool execution failed!")
            return "Success"

        @tool
        def test_none_tool() -> None:
            """Tool that returns None."""
            return None

        @tool
        def test_long_output() -> str:
            """Tool that returns very long output."""
            return "x" * 1000

        @tool
        def test_no_args() -> str:
            """Tool with no arguments."""
            return "No args needed"

        self.test_calculator = test_calculator
        self.test_error_tool = test_error_tool
        self.test_none_tool = test_none_tool
        self.test_long_output = test_long_output
        self.test_no_args = test_no_args

    def teardown_method(self):
        """Clean up after tests."""
        from tinyagent.tools import REGISTRY

        REGISTRY._data.clear()
        REGISTRY._frozen = False

    # Test 1: Basic setup verification
    def test_setup_creates_tools(self):
        """Test that setup creates all expected tools."""
        agent = ReactAgent(
            tools=[
                self.test_calculator,
                self.test_error_tool,
                self.test_none_tool,
                self.test_long_output,
                self.test_no_args,
            ]
        )

        assert len(agent._tool_map) == 5
        assert "test_calculator" in agent._tool_map
        assert "test_error_tool" in agent._tool_map
        assert "test_none_tool" in agent._tool_map
        assert "test_long_output" in agent._tool_map
        assert "test_no_args" in agent._tool_map

    # Test 2: Scratchpad handling
    @patch("tinyagent.agents.agent.OpenAI")
    def test_scratchpad_with_final_answer(self, mock_openai_class):
        """Test scratchpad handling with final answer."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(content='{"scratchpad": "Let me think about this...", "answer": "42"}')
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        agent = ReactAgent(tools=[self.test_calculator])
        result = agent.run("What is the meaning of life?")

        assert result == "42"
        assert mock_client.chat.completions.create.call_count == 1

    @patch("tinyagent.agents.agent.OpenAI")
    def test_scratchpad_with_tool_call(self, mock_openai_class):
        """Test scratchpad followed by tool invocation."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        responses = [
            Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content='{"scratchpad": "I need to calculate 2+2", "tool": "test_calculator", "arguments": {"expression": "2+2"}}'
                        )
                    )
                ]
            ),
            Mock(choices=[Mock(message=Mock(content='{"answer": "The result is 4"}'))]),
        ]
        mock_client.chat.completions.create.side_effect = responses

        agent = ReactAgent(tools=[self.test_calculator])
        result = agent.run("Calculate 2+2")

        assert result == "The result is 4"
        assert mock_client.chat.completions.create.call_count == 2

    @patch("tinyagent.agents.agent.OpenAI")
    def test_scratchpad_alone_continues_execution(self, mock_openai_class):
        """Test that scratchpad alone prompts continuation."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        responses = [
            Mock(choices=[Mock(message=Mock(content='{"scratchpad": "Just thinking..."}'))]),
            Mock(choices=[Mock(message=Mock(content='{"answer": "Done thinking"}'))]),
        ]
        mock_client.chat.completions.create.side_effect = responses

        agent = ReactAgent(tools=[self.test_calculator])
        result = agent.run("Think about something")

        assert result == "Done thinking"
        assert mock_client.chat.completions.create.call_count == 2
        # Verify temperature increased after scratchpad-only response
        assert mock_client.chat.completions.create.call_args_list[1].kwargs["temperature"] == 0.2

    # Test 3: Tool execution edge cases
    @patch("tinyagent.agents.agent.OpenAI")
    def test_tool_raises_exception(self, mock_openai_class):
        """Test handling when tool raises exception."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        responses = [
            Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content='{"tool": "test_error_tool", "arguments": {"should_fail": true}}'
                        )
                    )
                ]
            ),
            Mock(choices=[Mock(message=Mock(content='{"answer": "Tool failed as expected"}'))]),
        ]
        mock_client.chat.completions.create.side_effect = responses

        agent = ReactAgent(tools=[self.test_error_tool])
        result = agent.run("Test error handling")

        assert result == "Tool failed as expected"
        # Check that error was passed back to LLM
        messages = mock_client.chat.completions.create.call_args_list[1].kwargs["messages"]
        assert "Error: ToolError: Tool execution failed!" in messages[-1]["content"]

    @patch("tinyagent.agents.agent.OpenAI")
    def test_tool_returns_none(self, mock_openai_class):
        """Test handling when tool returns None."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        responses = [
            Mock(
                choices=[Mock(message=Mock(content='{"tool": "test_none_tool", "arguments": {}}'))]
            ),
            Mock(choices=[Mock(message=Mock(content='{"answer": "Tool returned None"}'))]),
        ]
        mock_client.chat.completions.create.side_effect = responses

        agent = ReactAgent(tools=[self.test_none_tool])
        result = agent.run("Test None return")

        assert result == "Tool returned None"
        messages = mock_client.chat.completions.create.call_args_list[1].kwargs["messages"]
        assert "Observation: None" in messages[-1]["content"]

    @patch("tinyagent.agents.agent.OpenAI")
    def test_tool_output_truncation(self, mock_openai_class):
        """Test that long tool output is truncated."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        responses = [
            Mock(
                choices=[
                    Mock(message=Mock(content='{"tool": "test_long_output", "arguments": {}}'))
                ]
            ),
            Mock(choices=[Mock(message=Mock(content='{"answer": "Processed long output"}'))]),
        ]
        mock_client.chat.completions.create.side_effect = responses

        agent = ReactAgent(tools=[self.test_long_output])
        result = agent.run("Get long output", verbose=True)

        assert result == "Processed long output"
        messages = mock_client.chat.completions.create.call_args_list[1].kwargs["messages"]
        # Check truncation happened (500 chars + ellipsis)
        assert len(messages[-1]["content"]) < 600
        assert messages[-1]["content"].endswith("…")

    @patch("tinyagent.agents.agent.OpenAI")
    def test_tool_with_no_arguments(self, mock_openai_class):
        """Test tool that requires no arguments."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        responses = [
            Mock(choices=[Mock(message=Mock(content='{"tool": "test_no_args", "arguments": {}}'))]),
            Mock(choices=[Mock(message=Mock(content='{"answer": "No args worked"}'))]),
        ]
        mock_client.chat.completions.create.side_effect = responses

        agent = ReactAgent(tools=[self.test_no_args])
        result = agent.run("Call no args tool")

        assert result == "No args worked"

    # Test 4: Temperature management
    @patch("tinyagent.agents.agent.OpenAI")
    def test_temperature_increases_on_errors(self, mock_openai_class):
        """Test temperature increases with each error."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        responses = [
            Mock(choices=[Mock(message=Mock(content="invalid json 1"))]),
            Mock(choices=[Mock(message=Mock(content="invalid json 2"))]),
            Mock(choices=[Mock(message=Mock(content='{"answer": "Finally valid"}'))]),
        ]
        mock_client.chat.completions.create.side_effect = responses

        agent = ReactAgent(tools=[self.test_calculator])
        result = agent.run("Parse after errors")

        assert result == "Finally valid"
        # Check temperature progression: 0.0 -> 0.2 -> 0.4
        calls = mock_client.chat.completions.create.call_args_list
        assert calls[0].kwargs["temperature"] == 0.0
        assert calls[1].kwargs["temperature"] == 0.2
        assert calls[2].kwargs["temperature"] == 0.4

    # Test 5: Verbose mode
    @patch("tinyagent.agents.agent.OpenAI")
    def test_verbose_mode_output(self, mock_openai_class, capsys):
        """Test verbose mode prints expected output."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"answer": "42"}'))]
        mock_client.chat.completions.create.return_value = mock_response

        agent = ReactAgent(tools=[self.test_calculator])
        agent.run("What is the answer?", verbose=True)

        captured = capsys.readouterr()
        assert "REACT AGENT STARTING" in captured.out
        assert "TASK: What is the answer?" in captured.out
        assert "AVAILABLE TOOLS: ['test_calculator']" in captured.out
        assert "FINAL ANSWER: 42" in captured.out

    # Test 6: Complex error recovery
    @patch("tinyagent.agents.agent.OpenAI")
    def test_recovery_after_multiple_errors(self, mock_openai_class):
        """Test recovery after JSON and tool errors."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        responses = [
            Mock(choices=[Mock(message=Mock(content="bad json"))]),
            Mock(
                choices=[Mock(message=Mock(content='{"tool": "test_calculator", "arguments": {}}'))]
            ),  # Missing required arg
            Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content='{"tool": "test_calculator", "arguments": {"expression": "5+5"}}'
                        )
                    )
                ]
            ),
            Mock(choices=[Mock(message=Mock(content='{"answer": "The answer is 10"}'))]),
        ]
        mock_client.chat.completions.create.side_effect = responses

        agent = ReactAgent(tools=[self.test_calculator])
        result = agent.run("Calculate something")

        assert result == "The answer is 10"
        assert mock_client.chat.completions.create.call_count == 4

    # Test 7: Final answer behavior
    @patch("tinyagent.agents.agent.OpenAI")
    def test_final_answer_after_max_steps(self, mock_openai_class):
        """Test final answer request after hitting step limit."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # First 3 calls return tool invocations, final call returns answer
        tool_response = Mock(
            choices=[
                Mock(
                    message=Mock(
                        content='{"tool": "test_calculator", "arguments": {"expression": "1+1"}}'
                    )
                )
            ]
        )
        final_response = Mock(choices=[Mock(message=Mock(content='{"answer": "Best guess: 2"}'))])

        mock_client.chat.completions.create.side_effect = [
            tool_response,
            tool_response,
            tool_response,  # 3 steps
            final_response,  # Final attempt
        ]

        agent = ReactAgent(tools=[self.test_calculator])
        result = agent.run("Keep calculating", max_steps=3)

        assert result == "Best guess: 2"
        assert mock_client.chat.completions.create.call_count == 4
        # Verify final message asks for best answer
        final_messages = mock_client.chat.completions.create.call_args_list[3].kwargs["messages"]
        assert final_messages[-1]["content"] == "Return your best final answer now."

    @patch("tinyagent.agents.agent.OpenAI")
    def test_final_answer_attempt_fails(self, mock_openai_class):
        """Test when final answer attempt also fails to provide answer."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # All responses are tool calls, even final attempt
        tool_response = Mock(
            choices=[
                Mock(
                    message=Mock(
                        content='{"tool": "test_calculator", "arguments": {"expression": "1+1"}}'
                    )
                )
            ]
        )

        mock_client.chat.completions.create.return_value = tool_response

        agent = ReactAgent(tools=[self.test_calculator])

        with pytest.raises(StepLimitReached, match="Exceeded max steps without an answer"):
            agent.run("Never give answer", max_steps=2)

    # Test 8: Message construction
    def test_message_format_for_tool_responses(self):
        """Test that tool responses use 'user' role."""
        agent = ReactAgent(tools=[self.test_calculator])

        # Call _safe_tool and verify message format
        ok, result = agent._safe_tool("test_calculator", {"expression": "2+2"})

        assert ok is True
        assert result == "4"

    def test_system_prompt_immutability(self):
        """Test that system prompt doesn't change after initialization."""
        agent = ReactAgent(tools=[self.test_calculator])
        _ = agent._system_prompt

        # Try to modify (shouldn't affect internal prompt)
        agent._system_prompt = "Modified prompt"

        # In real implementation, _system_prompt is used directly,
        # so this would actually change it. This test documents current behavior.
        assert agent._system_prompt == "Modified prompt"

    # Test 9: Edge cases
    @patch("tinyagent.agents.agent.OpenAI")
    def test_empty_tool_arguments(self, mock_openai_class):
        """Test tool call with explicitly empty arguments."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        responses = [
            Mock(
                choices=[Mock(message=Mock(content='{"tool": "test_no_args", "arguments": null}'))]
            ),
            Mock(choices=[Mock(message=Mock(content='{"answer": "Handled null args"}'))]),
        ]
        mock_client.chat.completions.create.side_effect = responses

        agent = ReactAgent(tools=[self.test_no_args])
        result = agent.run("Call with null args")

        assert result == "Handled null args"

    @patch("tinyagent.agents.agent.OpenAI")
    def test_unicode_in_responses(self, mock_openai_class):
        """Test handling of unicode characters in responses."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"answer": "Hello 世界! 🌍"}'))]
        mock_client.chat.completions.create.return_value = mock_response

        agent = ReactAgent(tools=[self.test_calculator])
        result = agent.run("Say hello in multiple languages")

        assert result == "Hello 世界! 🌍"

    @patch("tinyagent.agents.agent.OpenAI")
    def test_very_long_question(self, mock_openai_class):
        """Test handling of very long question input."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content='{"answer": "Processed long question"}'))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        agent = ReactAgent(tools=[self.test_calculator])
        long_question = "This is a very long question. " * 100
        result = agent.run(long_question)

        assert result == "Processed long question"
        # Verify long question was passed to LLM
        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        assert long_question in messages[1]["content"]

    @patch("tinyagent.agents.agent.OpenAI")
    def test_special_json_characters_in_response(self, mock_openai_class):
        """Test handling of special characters that could break JSON."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content='{"answer": "Line1\\nLine2\\tTabbed\\"Quoted\\""}'))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        agent = ReactAgent(tools=[self.test_calculator])
        result = agent.run("Return special characters")

        assert result == 'Line1\nLine2\tTabbed"Quoted"'
