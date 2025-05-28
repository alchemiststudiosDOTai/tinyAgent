#!/usr/bin/env python3

from tinyagent import tool, ReactAgent

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b

@tool
def divide(a: float, b: float) -> float:
    """Divide the first number by the second number."""
    return a / b

agent = ReactAgent(tools=[multiply, divide])
result = agent.run("What is 12 times 5, then divided by 3?")
print(f"\nFinal Answer: {result}")