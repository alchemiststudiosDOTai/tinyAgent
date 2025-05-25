import pytest
import sys
import pathlib
from typing import Union, Literal
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent

@tool
def calculate_math(
    a: Union[int, float], 
    b: Union[int, float], 
    operation: Literal['add', 'subtract', 'multiply', 'divide'] = 'add'
) -> Union[int, float]:
    """
    Perform basic mathematical operations on two numbers.
    
    Args:
        a: First number
        b: Second number
        operation: The operation to perform - 'add', 'subtract', 'multiply', or 'divide'
        
    Returns:
        The result of the operation
        
    Raises:
        ValueError: If division by zero is attempted
    """
    if operation == 'add':
        return a + b
    elif operation == 'subtract':
        return a - b
    elif operation == 'multiply':
        return a * b
    elif operation == 'divide':
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unsupported operation: {operation}")

# Test data as a list of tuples (query, expected_result, operation, a, b)
test_cases = [
    # Addition
    ("add 10 and 20", 30, 'add', 10, 20),
    ("what is 42 plus 58", 100, 'add', 42, 58),
    
    # Subtraction
    ("subtract 3 from 10", 7, 'subtract', 10, 3),
    ("what is 20 minus 5", 15, 'subtract', 20, 5),
    
    # Multiplication
    ("multiply 5 by 6", 30, 'multiply', 5, 6),
    ("what is 10 times 10", 100, 'multiply', 10, 10),
    
    # Division
    ("divide 10 by 2", 5, 'divide', 10, 2),
    ("what is 100 divided by 10", 10, 'divide', 100, 10),
]

# Division by zero test case
division_by_zero_cases = [
    ("divide 10 by 0", 'divide', 10, 0),
    ("what is 5 divided by 0", 'divide', 5, 0),
]

@pytest.fixture
def agent():
    """Fixture to create and return an agent instance."""
    return tiny_agent(tools=[calculate_math])

@pytest.mark.parametrize("query,expected,operation,a,b", test_cases, 
                         ids=[f"{query}" for query, _, _, _, _ in test_cases])
def test_agent_returns_correct_numbers(agent, query, expected, operation, a, b):
    """Test that the agent returns the correct results for various math operations."""
    if operation == 'divide' and isinstance(expected, float):
        result = agent.run(query, expected_type=float)
        assert abs(result - expected) < 1e-10  # Allow for floating point imprecision
    else:
        result = agent.run(query, expected_type=type(expected))
        assert result == expected

from tinyagent.exceptions import AgentRetryExceeded

@pytest.mark.parametrize("query", [
    "divide 10 by 0",
    "what is 5 divided by 0"
])
def test_division_by_zero(agent, query):
    """Test that division by zero is handled correctly."""
    try:
        result = agent.run(query)
        # If we get here, the agent returned a message instead of raising an exception
        result_lower = str(result).lower()
        assert any(term in result_lower for term in [
            "cannot divide by zero", 
            "division by zero", 
            "divide by zero",
            "failed to get valid response"  # AgentRetryExceeded case
        ]), f"Unexpected response to division by zero: {result}"
    except (ValueError, AgentRetryExceeded) as e:
        # For AgentRetryExceeded, we'll just verify that we got an error
        if isinstance(e, AgentRetryExceeded):
            assert "failed to get valid response" in str(e).lower(), \
                   f"Unexpected AgentRetryExceeded message: {e}"
        else:
            # For ValueError, check it's about division by zero
            error_msg = str(e).lower()
            assert any(term in error_msg for term in [
                "cannot divide by zero", 
                "division by zero", 
                "divide by zero"
            ]), f"Unexpected error message for division by zero: {error_msg}"

