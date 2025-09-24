"""
Integration tests for agent final answer functionality.
"""

from pathlib import Path
from unittest.mock import Mock, patch

from dotenv import load_dotenv

from tinyagent import ReactAgent, TinyCodeAgent, tool
from tinyagent.exceptions import StepLimitReached
from tinyagent.tools import get_registry
from tinyagent.types import RunResult

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")


class TestReactAgentIntegration:
    """Test ReactAgent with new final answer infrastructure."""

    def setup_method(self):
        """Set up test tools."""
        # Clear registry for clean test state
        from tinyagent.tools import REGISTRY
        REGISTRY._data.clear()
        REGISTRY._frozen = False

        # Create test tool
        @tool
        def calculator(expression: str) -> float:
            """Calculate a mathematical expression."""
            return eval(expression)  # nosec B307: safe for testing

        self.calculator = calculator
    """Test ReactAgent with new final answer infrastructure."""

    @patch("tinyagent.agents.agent.OpenAI")
    def test_run_with_return_result_normal_answer(self, mock_openai_class):
        """Test ReactAgent returning RunResult for normal answer."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"answer": "42"}'))]
        mock_client.chat.completions.create.return_value = mock_response

        agent = ReactAgent(tools=[self.calculator])
        result = agent.run("What is the answer?", return_result=True)

        assert isinstance(result, RunResult)
        assert result.output == "42"
        assert result.final_answer is not None
        assert result.final_answer.value == "42"
        assert result.final_answer.source == "normal"
        assert result.state == "completed"
        assert result.steps_taken == 1
        assert result.duration_seconds > 0
        assert result.error is None

    @patch("tinyagent.agents.agent.OpenAI")
    def test_run_with_return_result_final_attempt(self, mock_openai_class):
        """Test ReactAgent returning RunResult for final attempt answer."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # First 3 calls return tool invocations, final call returns answer
        tool_response = Mock(
            choices=[Mock(message=Mock(content='{"tool": "calculator", "arguments": {"expression": "1+1"}}'))]
        )
        final_response = Mock(choices=[Mock(message=Mock(content='{"answer": "Best guess: 2"}'))])

        mock_client.chat.completions.create.side_effect = [
            tool_response, tool_response, tool_response, final_response
        ]

        agent = ReactAgent(tools=[self.calculator])
        result = agent.run("Keep calculating", max_steps=3, return_result=True)
        
        assert isinstance(result, RunResult)
        assert result.output == "Best guess: 2"
        assert result.final_answer is not None
        assert result.final_answer.value == "Best guess: 2"
        assert result.final_answer.source == "final_attempt"
        assert result.state == "step_limit_reached"
        assert result.steps_taken == 3
        assert result.duration_seconds > 0
        assert result.error is None

    @patch("tinyagent.agents.agent.OpenAI")
    def test_run_with_return_result_step_limit_no_answer(self, mock_openai_class):
        """Test ReactAgent returning RunResult when step limit reached with no answer."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # All responses are tool calls, even final attempt
        tool_response = Mock(
            choices=[Mock(message=Mock(content='{"tool": "calculator", "arguments": {"expression": "1+1"}}'))]
        )
        mock_client.chat.completions.create.return_value = tool_response

        agent = ReactAgent(tools=[self.calculator])
        result = agent.run("Never give answer", max_steps=2, return_result=True)

        assert isinstance(result, RunResult)
        assert result.output == ""
        assert result.final_answer is None
        assert result.state == "step_limit_reached"
        assert result.steps_taken == 2
        assert result.duration_seconds > 0
        assert isinstance(result.error, StepLimitReached)

    @patch("tinyagent.agents.agent.OpenAI")
    def test_backward_compatibility_string_return(self, mock_openai_class):
        """Test that ReactAgent still returns string by default."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"answer": "42"}'))]
        mock_client.chat.completions.create.return_value = mock_response

        agent = ReactAgent(tools=[self.calculator])
        result = agent.run("What is the answer?")  # return_result=False by default

        assert isinstance(result, str)
        assert result == "42"


class TestTinyCodeAgentIntegration:
    """Test TinyCodeAgent with new final answer infrastructure."""

    def setup_method(self):
        """Set up test tools."""
        @tool
        def calculator(expression: str) -> float:
            """Calculate a mathematical expression."""
            return eval(expression)  # nosec B307: safe for testing

        self.calculator = calculator

    def test_run_with_return_result_normal_answer(self):
        """Test TinyCodeAgent returning RunResult for normal answer."""
        agent = TinyCodeAgent(tools=[self.calculator])
        
        with patch.object(agent, "_chat") as mock_chat:
            mock_chat.return_value = """```python
final_answer("The answer is 42")
```"""
            
            result = agent.run("What is the answer?", return_result=True)
            
            assert isinstance(result, RunResult)
            assert result.output == "The answer is 42"
            assert result.final_answer is not None
            assert result.final_answer.value == "The answer is 42"
            assert result.final_answer.source == "normal"
            assert result.state == "completed"
            assert result.steps_taken == 1
            assert result.duration_seconds > 0
            assert result.error is None

    def test_run_with_return_result_final_attempt_code(self):
        """Test TinyCodeAgent returning RunResult for final attempt with code."""
        agent = TinyCodeAgent(tools=[self.calculator])
        
        with patch.object(agent, "_chat") as mock_chat:
            # First 3 calls return non-final code, final attempt returns answer
            responses = [
                """```python
print("Step 1")
```""",
                """```python
print("Step 2")
```""",
                """```python
print("Step 3")
```""",
                """```python
final_answer("Final attempt answer")
```"""
            ]
            mock_chat.side_effect = responses
            
            result = agent.run("Solve this", max_steps=3, return_result=True)
            
            assert isinstance(result, RunResult)
            assert result.output == "Final attempt answer"
            assert result.final_answer is not None
            assert result.final_answer.value == "Final attempt answer"
            assert result.final_answer.source == "final_attempt"
            assert result.state == "step_limit_reached"
            assert result.steps_taken == 3
            assert result.duration_seconds > 0
            assert result.error is None

    def test_run_with_return_result_final_attempt_json(self):
        """Test TinyCodeAgent returning RunResult for final attempt with JSON."""
        agent = TinyCodeAgent(tools=[self.calculator])
        
        with patch.object(agent, "_chat") as mock_chat:
            # First 3 calls return non-final code, final attempt returns JSON
            responses = [
                """```python
print("Step 1")
```""",
                """```python
print("Step 2")
```""",
                """```python
print("Step 3")
```""",
                """{"answer": "JSON final answer"}"""
            ]
            mock_chat.side_effect = responses
            
            result = agent.run("Solve this", max_steps=3, return_result=True)
            
            assert isinstance(result, RunResult)
            assert result.output == "JSON final answer"
            assert result.final_answer is not None
            assert result.final_answer.value == "JSON final answer"
            assert result.final_answer.source == "final_attempt"
            assert result.state == "step_limit_reached"
            assert result.steps_taken == 3
            assert result.duration_seconds > 0
            assert result.error is None

    def test_run_with_return_result_step_limit_no_answer(self):
        """Test TinyCodeAgent returning RunResult when step limit reached with no answer."""
        agent = TinyCodeAgent(tools=[self.calculator])
        
        with patch.object(agent, "_chat") as mock_chat:
            # Never provide final answer
            mock_chat.return_value = """```python
print("Still thinking...")
```"""
            
            result = agent.run("Solve this", max_steps=2, return_result=True)
            
            assert isinstance(result, RunResult)
            assert result.output == ""
            assert result.final_answer is None
            assert result.state == "step_limit_reached"
            assert result.steps_taken == 2
            assert result.duration_seconds > 0
            assert isinstance(result.error, StepLimitReached)

    def test_backward_compatibility_string_return(self):
        """Test that TinyCodeAgent still returns string by default."""
        agent = TinyCodeAgent(tools=[self.calculator])
        
        with patch.object(agent, "_chat") as mock_chat:
            mock_chat.return_value = """```python
final_answer("The answer is 42")
```"""
            
            result = agent.run("What is the answer?")  # return_result=False by default
            
            assert isinstance(result, str)
            assert result == "The answer is 42"


class TestUnifiedBehavior:
    """Test that both agents behave consistently."""

    def setup_method(self):
        """Set up test tools."""
        @tool
        def calculator(expression: str) -> float:
            return eval(expression)
        self.calculator = calculator

    def test_both_agents_support_return_result(self):
        """Test that both agents support return_result parameter."""
        react_agent = ReactAgent(tools=[self.calculator])
        code_agent = TinyCodeAgent(tools=[self.calculator])
        
        # Both should have the parameter in their run method signature
        import inspect
        
        react_sig = inspect.signature(react_agent.run)
        code_sig = inspect.signature(code_agent.run)
        
        assert "return_result" in react_sig.parameters
        assert "return_result" in code_sig.parameters
        
        # Both should default to False
        assert react_sig.parameters["return_result"].default is False
        assert code_sig.parameters["return_result"].default is False
