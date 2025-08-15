#!/usr/bin/env python3
"""Test the final optimized prompt"""

from dotenv import load_dotenv

from tinyagent import ReactAgent, tool

load_dotenv()


@tool
def calculator(expression: str) -> float:
    """Evaluate a mathematical expression"""
    return eval(expression)


@tool
def get_weather(city: str) -> dict:
    """Get weather for a city"""
    return {
        "Tokyo": {"temp": 22, "condition": "Sunny"},
        "London": {"temp": 15, "condition": "Rainy"},
    }.get(city, {"temp": 20, "condition": "Unknown"})


print("Testing Final Optimized Prompt (Tip-Motivated + Structured)")
print("=" * 70)

tests = [
    ("Simple calc", "What is 25% of 80?", [calculator]),
    ("Multi-step", "Calculate 20% of 150, then add 10", [calculator]),
    ("Weather", "Compare weather in Tokyo and London", [get_weather]),
]

for test_name, query, tools in tests:
    print(f"\n{test_name}: {query}")
    print("-" * 40)

    agent = ReactAgent(tools=tools, model="gpt-4o-mini")

    try:
        # Run with verbose to see the reasoning
        result = agent.run(query, max_steps=5, verbose=True)
        print(f"\nFINAL ANSWER: {result}")
    except Exception as e:
        print(f"ERROR: {e}")

    print("\n" + "=" * 70)
