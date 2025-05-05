import pytest
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent

@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b

# Test data as a list of tuples (query, expected_result)
test_cases = [
    ("calculate the sum of 5 and 3", 8),         # Basic case
    ("add 10 and 20", 30),                       # Simple addition
    ("what is 42 plus 58", 100),                 # Different phrasing
    ("sum up 100 and 200", 300),                 # Large numbers
    ("what's the total of 25 and 75", 100),      # Different phrasing with apostrophe
    ("compute 7 + (-12)", -5),                   # Negative number with explicit sign
    ("find the sum of -10 and -20", -30),        # Two negative numbers
    ("calculate 1000 plus 337", 1337),           # Larger sum
    ("add zero and zero", 0),                    # Zero case
]

@pytest.fixture
def agent():
    """Fixture to create and return an agent instance."""
    return tiny_agent(tools=[calculate_sum])

@pytest.mark.parametrize("query,expected", test_cases, 
                         ids=[f"query: {query}" for query, _ in test_cases])
def test_agent_returns_correct_numbers(agent, query, expected):
    """Test that the agent returns the correct numbers for various inputs."""
    result = agent.run(query, expected_type=int)
    assert result == expected

