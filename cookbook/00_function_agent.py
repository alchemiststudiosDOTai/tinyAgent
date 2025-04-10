
#!/usr/bin/env python3
"""
Example 0: Functions as Agents

This example demonstrates the fundamental philosophy of tinyAgent:
turning any function into a tool or agent with minimal configuration.
"""
import os
import sys
# Add parent directory to the path so we can import the core package: When the pip package is installed, we won't need this
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tinyagent.decorators import tool
from tinyagent.factory.agent_factory import AgentFactory

# Define a simple calculator function and turn it into a tool
@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b
def main():
    """Create a basic agent with a calculator tool."""
    # One-liner: create agent with our tool directly
    agent = AgentFactory.get_instance().create_agent(tools=[calculate_sum])
    # Run the agent with a query
    query = "calculate the sum of 5 and 3"
    print(f"Running agent with query: '{query}'")
    # you can also specify the expected type of the result
    result = agent.run(query, expected_type=int)
    print(f"Result: {result}")
    print(f"Result Type: {type(result)}")


if __name__ == "__main__":
    main()
