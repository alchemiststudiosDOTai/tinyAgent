#!/usr/bin/env python3
"""Test the minimal ReactAgent example to ensure it works correctly."""


from tinyagent import ReactAgent, tool
from tinyagent.react.react_agent import Scratchpad


def test_react_minimal_example():
    """Test the minimal example with multiply and divide operations."""

    @tool
    def multiply(a: float, b: float) -> float:
        """Multiply two numbers together."""
        return a * b

    @tool
    def divide(a: float, b: float) -> float:
        """Divide the first number by the second number."""
        return a / b

    # Mock LLM responses for deterministic testing
    responses = [
        """Thought: First, I need to multiply 12 by 5.
Action: multiply
Action Input: {"a": 12, "b": 5}""",
        """Thought: Now I need to divide 60 by 3.
Action: divide
Action Input: {"a": 60, "b": 3}""",
        """Thought: The final result is 20.
Action: final_answer
Action Input: {"answer": 20}""",
    ]

    def mock_llm(prompt):
        return responses.pop(0)

    agent = ReactAgent(tools=[multiply, divide])
    result = agent.run("What is 12 times 5, then divided by 3?", llm_callable=mock_llm)

    # The result should be 20 (as a string since final_answer returns strings)
    assert result == "20", f"Expected '20', got '{result}'"


def test_react_minimal_with_string_answer():
    """Test that the agent can return string answers too."""

    @tool
    def multiply(a: float, b: float) -> float:
        """Multiply two numbers together."""
        return a * b

    responses = [
        """Thought: I need to multiply 6 by 7.
Action: multiply
Action Input: {"a": 6, "b": 7}""",
        """Thought: The result is 42.
Action: final_answer
Action Input: {"answer": "The answer is 42"}""",
    ]

    def mock_llm(prompt):
        return responses.pop(0)

    agent = ReactAgent(tools=[multiply])
    result = agent.run("What is 6 times 7?", llm_callable=mock_llm)

    assert result == "The answer is 42", f"Expected 'The answer is 42', got '{result}'"


def test_react_minimal_divide_by_zero():
    """Test error handling for division by zero."""

    @tool
    def divide(a: float, b: float) -> float:
        """Divide the first number by the second number."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

    responses = [
        """Thought: I need to divide 10 by 0.
Action: divide
Action Input: {"a": 10, "b": 0}""",
        """Thought: There was an error dividing by zero.
Action: final_answer
Action Input: {"answer": "Error: Cannot divide by zero"}""",
    ]

    def mock_llm(prompt):
        return responses.pop(0)

    agent = ReactAgent(tools=[divide])
    result = agent.run("What is 10 divided by 0?", llm_callable=mock_llm)

    # The agent should handle the error gracefully
    assert "Error" in result or "Cannot divide by zero" in result


def test_react_custom_system_prompt():
    """Ensure custom system prompt is used."""

    @tool
    def echo(msg: str) -> str:
        return msg

    agent = ReactAgent(tools=[echo], system_prompt="My custom system prompt")
    prompt = agent._create_prompt("hi", Scratchpad())

    assert prompt.startswith("My custom system prompt")


if __name__ == "__main__":
    test_react_minimal_example()
    print("✅ test_react_minimal_example passed")

    test_react_minimal_with_string_answer()
    print("✅ test_react_minimal_with_string_answer passed")

    test_react_minimal_divide_by_zero()
    print("✅ test_react_minimal_divide_by_zero passed")

    print("\nAll minimal example tests passed!")
