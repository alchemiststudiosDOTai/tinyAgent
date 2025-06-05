# Standard library imports
import os
import sys

# Setup path for local package imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Local package imports
from tinyagent.agent import tiny_agent
from tinyagent.decorators import tool


@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    print(f"Executing calculate_sum({a}, {b})")
    return a + b


def test_with_tracing():
    """Test agent with tracing enabled."""
    print("\n--- Test with Tracing ---")
    # trace_this_agent=True means YES tracing
    agent = tiny_agent(tools=[calculate_sum], trace_this_agent=True)
    query = "calculate the sum of 100 and 23"
    result = agent.run(query, expected_type=int)
    print(f"Result: {result}")


def test_without_tracing():
    """Test agent with tracing disabled."""
    print("\n--- Test without Tracing ---")
    # No trace_this_agent means NO tracing
    agent = tiny_agent(tools=[calculate_sum])
    query = "calculate the sum of 55 and 11"
    result = agent.run(query, expected_type=int)
    print(f"Result: {result}")


if __name__ == "__main__":
    print("\nRunning Observability Tests...")
    test_without_tracing()
    test_with_tracing()
    print("\nTests Complete.\n")
