#!/usr/bin/env python3
"""
Simple TinyAgent Demo - Basic usage example

This demonstrates the minimal setup needed for users who install via pip:
pip install tiny-agent-os

This example shows:
1. Simple tool decoration with @tool
2. Basic ReactAgent setup
3. Multi-step problem solving
"""

from tinyagent import ReactAgent, tool


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b


@tool
def divide(a: float, b: float) -> float:
    """Divide the first number by the second number."""
    return a / b


@tool
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b


@tool
def subtract(a: float, b: float) -> float:
    """Subtract the second number from the first number."""
    return a - b


def main():
    """Simple calculator agent example."""
    # Create agent with basic math tools
    agent = ReactAgent(tools=[multiply, divide, add, subtract])

    print("TinyAgent Simple Demo")
    print("=" * 30)

    # Example 1: Multi-step calculation
    print("\n1. Multi-step calculation:")
    result = agent.run("What is 12 times 5, then divided by 3?")
    print(f"Result: {result}")

    # Example 2: More complex math
    print("\n2. Complex calculation:")
    result = agent.run("Calculate (15 + 25) * 2, then subtract 10")
    print(f"Result: {result}")

    # Example 3: Division with explanation
    print("\n3. Division problem:")
    result = agent.run(
        "If I have 100 dollars and want to split it equally among 7 people, how much does each person get?"
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
