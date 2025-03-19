#!/usr/bin/env python3
"""
Example 1: Basic Agent Creation

This example shows the simplest way to create a TinyAgent with minimal configuration.
"""

import os
import sys

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import Agent
from core.factory.agent_factory import AgentFactory


def main():
    """Create and run a basic agent with a simple calculator tool."""
    # Get the singleton factory instance
    factory = AgentFactory.get_instance()
    
    # Create calculator tool
    factory.create_tool(
        name="calculator",
        description="Perform basic arithmetic operations (add, subtract, multiply, divide)",
        func=calculate
    )
    
    # Create an agent that will use the factory
    agent = Agent(factory=factory)
    
    # Run the agent with a query
    print("Running agent with query: 'Calculate 5 + 3'")
    try:
        result = agent.run("Calculate 5 + 3")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")


def calculate(operation: str, a: float, b: float) -> float:
    """Calculator tool implementation."""
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else ValueError("Cannot divide by zero")
    }
    
    if operation not in operations:
        raise ValueError(f"Unknown operation: {operation}. Valid operations are: {', '.join(operations.keys())}")
    
    result = operations[operation](a, b)
    if isinstance(result, ValueError):
        raise result
    return result


if __name__ == "__main__":
    main()
