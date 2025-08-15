#!/usr/bin/env python3
"""Test the improved prompts"""

from dotenv import load_dotenv

from tinyagent import ReactAgent, TinyCodeAgent, tool

load_dotenv()


# Test tools
@tool
def calculator(expression: str) -> float:
    """Evaluate a mathematical expression"""
    return eval(expression)


@tool
def get_weather(city: str) -> dict:
    """Get weather for a city"""
    data = {
        "Tokyo": {"temp": 22, "condition": "Sunny", "humidity": 65},
        "London": {"temp": 15, "condition": "Rainy", "humidity": 80},
        "Miami": {"temp": 28, "condition": "Sunny", "humidity": 75},
    }
    return data.get(city, {"temp": 20, "condition": "Unknown", "humidity": 50})


print("Testing Improved TinyAgent Prompts")
print("=" * 60)

# Test 1: Simple calculation with ReactAgent
print("\n1. ReactAgent - Simple Calculation")
print("-" * 40)
agent = ReactAgent(tools=[calculator], model="gpt-4o-mini")
result = agent.run("What is 25% of 80?", verbose=True)
print(f"\nResult: {result}")

# Test 2: Multi-step with reasoning
print("\n\n2. ReactAgent - Weather Comparison")
print("-" * 40)
agent = ReactAgent(tools=[get_weather], model="gpt-4o-mini")
result = agent.run(
    "Compare the weather in Tokyo and London. Which is better for outdoor activities?", verbose=True
)
print(f"\nResult: {result}")

# Test 3: Code agent
print("\n\n3. TinyCodeAgent - Calculation")
print("-" * 40)
code_agent = TinyCodeAgent(tools=[calculator], model="gpt-4o-mini", extra_imports=["math"])
result = code_agent.run("Calculate the area of a circle with radius 5", verbose=True)
print(f"\nResult: {result}")
