#!/usr/bin/env python3
"""Test different prompt variations"""

import os
import time

from prompt_variations import PROMPT_VARIANTS
from tinyagent import ReactAgent, tool


# Mock tools for testing
@tool
def calculator(expression: str) -> float:
    """Evaluate a mathematical expression"""
    try:
        return eval(expression)
    except Exception:
        return 0.0  # Return 0 on error


@tool
def get_weather(city: str) -> dict:
    """Get weather for a city"""
    data = {
        "Tokyo": {"temp": 22, "condition": "Sunny", "humidity": 65},
        "London": {"temp": 15, "condition": "Rainy", "humidity": 80},
        "Miami": {"temp": 28, "condition": "Sunny", "humidity": 75},
    }
    return data.get(city, {"temp": 20, "condition": "Unknown", "humidity": 50})


# Test queries
TEST_QUERIES = [
    "What is 15% of 200?",
    "Compare the weather in Tokyo and London",
    "Is Miami good for beach activities today?",
]


def test_variant(name, prompt):
    """Test a single prompt variant"""
    print(f"\n{'=' * 60}")
    print(f"Testing: {name}")
    print(f"{'=' * 60}")

    # Temporarily override the SYSTEM prompt
    import tinyagent.prompt as prompt_module

    original = prompt_module.SYSTEM
    prompt_module.SYSTEM = prompt

    results = []

    try:
        for query in TEST_QUERIES:
            print(f"\nQuery: {query}")
            agent = ReactAgent(tools=[calculator, get_weather], model="gpt-4o-mini")

            try:
                start = time.time()
                answer = agent.run(query, max_steps=5, verbose=False)
                elapsed = time.time() - start

                print(f"✓ Answer: {answer[:100]}...")
                print(f"  Time: {elapsed:.2f}s")
                results.append({"success": True, "time": elapsed})

            except Exception as e:
                print(f"✗ Error: {e}")
                results.append({"success": False, "error": str(e)})

    finally:
        prompt_module.SYSTEM = original

    # Summary
    success_rate = sum(1 for r in results if r.get("success", False)) / len(results)
    avg_time = sum(r.get("time", 0) for r in results if r.get("success", False)) / max(
        1, sum(1 for r in results if r.get("success", False))
    )

    print("\nSummary:")
    print(f"  Success rate: {success_rate:.0%}")
    print(f"  Avg time: {avg_time:.2f}s")

    return success_rate, avg_time


def main():
    print("Testing TinyAgent Prompt Variations")
    print("=" * 80)

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set, using from .env")

    results = {}

    # Test each variant
    for name, prompt in PROMPT_VARIANTS.items():
        success_rate, avg_time = test_variant(name, prompt)
        results[name] = {"success_rate": success_rate, "avg_time": avg_time}
        time.sleep(1)  # Rate limiting

    # Final comparison
    print(f"\n{'=' * 80}")
    print("FINAL COMPARISON")
    print(f"{'=' * 80}")
    print(f"{'Variant':<20} {'Success Rate':<15} {'Avg Time':<10}")
    print("-" * 45)

    for name, metrics in results.items():
        print(f"{name:<20} {metrics['success_rate']:<15.0%} {metrics['avg_time']:<10.2f}s")

    # Find best
    best = max(results.items(), key=lambda x: x[1]["success_rate"])
    print(f"\nBest performer: {best[0]} ({best[1]['success_rate']:.0%} success)")


if __name__ == "__main__":
    main()
