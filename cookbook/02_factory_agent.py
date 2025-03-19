#!/usr/bin/env python3
"""
Example 2: Using AgentFactory

This example shows how to use the AgentFactory to create and manage agents,
which provides additional features like rate limiting and centralized tool management.
"""

import os
import sys

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factory.agent_factory import AgentFactory
from core.tool import Tool
from core.agent import Agent


def main():
    """Create and run an agent using the AgentFactory."""
    # Get the singleton factory instance
    factory = AgentFactory.get_instance()
    
    # Create calculator tool
    factory.create_tool(
        name="calculator",
        description="Perform basic arithmetic operations (add, subtract, multiply, divide)",
        func=calculate
    )
    
    # Create echo tool
    factory.create_tool(
        name="echo",
        description="Echo back any message or text that is provided",
        func=echo_message
    )
    
    # Create an agent that will use the factory
    agent = Agent(factory=factory, model="deepseek/deepseek-chat")
    
    # Run the agent with different queries
    queries = [
        "Calculate 10 - 5",
        "Add the numbers 7 and 3",
        "Multiply 4 and 6",
        "Echo hello world",
        "Please repeat: Python is awesome"
    ]
    
    for query in queries:
        print(f"\nRunning agent with query: '{query}'")
        try:
            result = agent.run(query)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")
    
    # Show tool usage statistics
    print("\nTool usage statistics:")
    status = factory.get_status()
    for tool_name, stats in status["tools"].items():
        print(f"  {tool_name}: {stats['calls']}/{stats['limit']} calls")


def calculate(operation: str, a: float, b: float) -> float:
    """
    Calculator tool implementation.
    
    Args:
        operation: The arithmetic operation to perform (add, subtract, multiply, divide)
        a: First number
        b: Second number
        
    Returns:
        float: Result of the arithmetic operation
        
    Raises:
        ValueError: If operation is unknown or if dividing by zero
    """
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


def echo_message(message: str) -> str:
    """
    Echo tool implementation.
    
    Args:
        message: The message to echo back
        
    Returns:
        str: The echoed message with a prefix
    """
    return f"Echo: {message}"


if __name__ == "__main__":
    main()
