#!/usr/bin/env python3
"""Actually test all prompt variations"""

import time

from dotenv import load_dotenv

from prompt_variations import PROMPT_VARIANTS
from tinyagent import tool

load_dotenv()


# Simple tools
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


# Test queries
TESTS = [
    ("simple_calc", "What is 25% of 80?", [calculator]),
    (
        "weather_compare",
        "Compare weather in Tokyo and London. Which is better for outdoor activities?",
        [get_weather],
    ),
    ("multi_step", "Calculate 15% tip on $45.50", [calculator]),
]


def test_variant(name, prompt_text):
    """Test a prompt variant"""
    print(f"\n{'=' * 70}")
    print(f"VARIANT: {name}")
    print(f"{'=' * 70}")

    # Create a new module to properly isolate prompts
    import importlib

    import tinyagent.prompt

    # Save original
    original_system = tinyagent.prompt.SYSTEM

    # Override
    tinyagent.prompt.SYSTEM = prompt_text

    # Need to reload agent module to pick up new prompt
    import tinyagent.agent

    importlib.reload(tinyagent.agent)

    results = []

    try:
        for test_name, query, tools in TESTS:
            print(f"\nTest: {test_name}")
            print(f"Query: {query}")

            try:
                # Create fresh agent
                agent = tinyagent.agent.ReactAgent(tools=tools, model="gpt-4o-mini")

                start = time.time()

                # Capture verbose output
                import contextlib
                import io

                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    answer = agent.run(query, max_steps=5, verbose=True)

                elapsed = time.time() - start
                output = buffer.getvalue()

                # Count JSON errors and scratchpad usage
                json_errors = output.count("JSON PARSE ERROR")
                scratchpad_uses = output.count("[SCRATCHPAD]:")
                steps = output.count("STEP")

                print(f"✓ Success in {elapsed:.2f}s")
                print(
                    f"  Steps: {steps}, JSON errors: {json_errors}, Scratchpad uses: {scratchpad_uses}"
                )
                print(f"  Answer: {answer[:80]}...")

                results.append(
                    {
                        "test": test_name,
                        "success": True,
                        "time": elapsed,
                        "steps": steps,
                        "json_errors": json_errors,
                        "scratchpad_uses": scratchpad_uses,
                        "answer": answer,
                    }
                )

            except Exception as e:
                print(f"✗ Failed: {str(e)[:100]}")
                results.append({"test": test_name, "success": False, "error": str(e)})

            time.sleep(0.5)  # Rate limit

    finally:
        # Restore original
        tinyagent.prompt.SYSTEM = original_system
        importlib.reload(tinyagent.agent)

    return results


def main():
    print("Testing TinyAgent Prompt Variations")
    print("=" * 70)

    all_results = {}

    # Test each variant
    for name, prompt in PROMPT_VARIANTS.items():
        results = test_variant(name, prompt)
        all_results[name] = results
        time.sleep(1)

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(
        f"\n{'Variant':<20} {'Success':<10} {'Avg Time':<10} {'Avg Steps':<10} {'JSON Errs':<10} {'Scratchpad':<10}"
    )
    print("-" * 70)

    for variant, results in all_results.items():
        successful = [r for r in results if r.get("success")]
        if successful:
            avg_time = sum(r["time"] for r in successful) / len(successful)
            avg_steps = sum(r.get("steps", 0) for r in successful) / len(successful)
            total_errors = sum(r.get("json_errors", 0) for r in successful)
            total_scratchpad = sum(r.get("scratchpad_uses", 0) for r in successful)
            success_rate = len(successful) / len(results)

            print(
                f"{variant:<20} {success_rate:<10.0%} {avg_time:<10.2f} {avg_steps:<10.1f} {total_errors:<10} {total_scratchpad:<10}"
            )
        else:
            print(f"{variant:<20} {'0%':<10} {'-':<10} {'-':<10} {'-':<10} {'-':<10}")

    # Find best
    best_time = min(
        (
            v,
            sum(r["time"] for r in rs if r.get("success"))
            / len([r for r in rs if r.get("success")]),
        )
        for v, rs in all_results.items()
        if any(r.get("success") for r in rs)
    )
    best_scratchpad = max(
        (v, sum(r.get("scratchpad_uses", 0) for r in rs)) for v, rs in all_results.items()
    )

    print(f"\nFastest: {best_time[0]} ({best_time[1]:.2f}s avg)")
    print(f"Most reasoning: {best_scratchpad[0]} ({best_scratchpad[1]} scratchpad uses)")


if __name__ == "__main__":
    main()
