"""Test Reasoning agent scratchpad functionality."""

import json
from typing import List

from tinyagent.reasoning_agent.reasoning_agent import (
    ReasoningAgent,
    Scratchpad,
    ThoughtStep,
    ActionStep,
    ObservationStep,
)
from tinyagent.decorators import tool


def test_scratchpad_formatting():
    """Test that scratchpad formats history correctly."""
    scratchpad = Scratchpad()
    
    # Add steps
    scratchpad.add(ThoughtStep("I need to add two numbers"))
    scratchpad.add(ActionStep(tool="add", args={"a": 1, "b": 2}))
    scratchpad.add(ObservationStep(result=3))
    
    # Check formatting
    formatted = scratchpad.format()
    expected_lines = [
        "Thought: I need to add two numbers",
        'Action: {"tool": "add", "args": {"a": 1, "b": 2}}',
        "Observation: 3"
    ]
    
    assert formatted == "\n".join(expected_lines)


def test_reasoning_multi_step_with_scratchpad():
    """Test Reasoning agent with multi-step execution and scratchpad tracking."""
    # Create tools
    @tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    @tool
    def multiply(a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b
    
    # Track prompts to verify scratchpad usage
    prompts_received = []
    
    # Mock LLM responses for multi-step calculation
    responses = [
        # Step 1: Add 10 + 20
        json.dumps({
            "thought": "First, I need to add 10 and 20",
            "action": {"tool": "add", "args": {"a": 10, "b": 20}}
        }),
        # Step 2: Multiply result by 3
        json.dumps({
            "thought": "Now I'll multiply the result 30 by 3",
            "action": {"tool": "multiply", "args": {"a": 30, "b": 3}}
        }),
        # Step 3: Final answer
        json.dumps({
            "thought": "The final result is 90",
            "action": {"tool": "final_answer", "args": {"answer": "90"}}
        })
    ]
    
    def mock_llm(prompt: str) -> str:
        prompts_received.append(prompt)
        return responses.pop(0)
    
    # Create agent and run
    agent = ReasoningAgent()
    agent.register_tool(add._tool)
    agent.register_tool(multiply._tool)
    
    result = agent.run_reasoning(
        "Calculate (10 + 20) * 3",
        llm_callable=mock_llm,
        max_steps=5
    )
    
    # Verify result
    assert result == "90"
    
    # Verify we received 3 prompts
    assert len(prompts_received) == 3
    
    # Check first prompt has no previous steps
    assert "Previous steps:" not in prompts_received[0]
    
    # Check second prompt includes first step
    second_prompt = prompts_received[1]
    assert "Previous steps:" in second_prompt
    assert "Thought: First, I need to add 10 and 20" in second_prompt
    assert '"tool": "add"' in second_prompt
    assert "Observation: 30" in second_prompt
    
    # Check third prompt includes both steps
    third_prompt = prompts_received[2]
    assert "Previous steps:" in third_prompt
    assert "Thought: First, I need to add 10 and 20" in third_prompt
    assert "Thought: Now I'll multiply the result 30 by 3" in third_prompt
    assert "Observation: 30" in third_prompt
    assert "Observation: 90" in third_prompt


def test_reasoning_max_steps_limit():
    """Test that Reasoning agent respects max_steps limit."""
    @tool
    def dummy_tool() -> str:
        """Dummy tool for testing."""
        return "result"
    
    # Create LLM that never gives final answer
    def endless_llm(_prompt: str) -> str:
        return json.dumps({
            "thought": "Still thinking...",
            "action": {"tool": "dummy_tool", "args": {}}
        })
    
    agent = ReasoningAgent()
    agent.register_tool(dummy_tool._tool)
    
    # Should return None after max_steps
    result = agent.run_reasoning(
        "Do something",
        llm_callable=endless_llm,
        max_steps=3
    )
    
    assert result is None


def test_reasoning_with_framework_integration():
    """Test Reasoning agent using framework's JSON parsing."""
    @tool
    def echo(message: str) -> str:
        """Echo a message."""
        return message
    
    # Test various response formats that robust_json_parse should handle
    responses = [
        # Markdown wrapped JSON
        '```json\n{"thought": "I need to echo the message", "action": {"tool": "echo", "args": {"message": "hello"}}}\n```',
        # Plain JSON for final answer
        '{"thought": "Done echoing", "action": {"tool": "final_answer", "args": {"answer": "hello"}}}'
    ]
    
    def mock_llm(_prompt: str) -> str:
        return responses.pop(0)
    
    agent = ReasoningAgent()
    agent.register_tool(echo._tool)
    
    result = agent.run_reasoning(
        "Echo the word hello",
        llm_callable=mock_llm
    )
    
    assert result == "hello"


if __name__ == "__main__":
    test_scratchpad_formatting()
    print("✓ Scratchpad formatting test passed")
    
    test_reasoning_multi_step_with_scratchpad()
    print("✓ Multi-step Reasoning with scratchpad test passed")
    
    test_reasoning_max_steps_limit()
    print("✓ Max steps limit test passed")
    
    test_reasoning_with_framework_integration()
    print("✓ Framework integration test passed")
    
    print("\nAll tests passed! 🎉")