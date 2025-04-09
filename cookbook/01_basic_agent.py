#!/usr/bin/env python3
"""
Example 1: Basic Agent Creation

This example shows the simplest way to create a TinyAgent with minimal
configuration. We also parse the final result as an integer.
"""

import os
import sys

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tinyagent.agent import Agent


def main():
    """Create a basic agent, run it with a query, and request an integer result."""
    # 1. Example query
    query = "what is 5 + 3"
    print(f"Running agent with query: '{query}'")
    agent = Agent()

    # 3. Run the agent, requesting an integer result using the hint
    result = agent.run(query, expected_type=int)
    # 4. Print the result and its type
    print(f"\nResult: {result}")
    print(f"Result Type: {type(result)}")

if __name__ == "__main__":
    main()
