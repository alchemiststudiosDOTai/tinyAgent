#!/usr/bin/env python3
"""Test all prompt variations with detailed metrics"""

import contextlib
import io
import time

from dotenv import load_dotenv

from prompt_variations import PROMPT_VARIANTS
from tinyagent import ReactAgent, tool

load_dotenv()


@tool
def calculator(expression: str) -> float:
    """Evaluate a mathematical expression"""
    return eval(expression)


@tool
def get_weather(city: str) -> dict:
    """Get weather for a city"""
    data = {
        "Tokyo": {"temp": 22, "condition": "Sunny"},
        "London": {"temp": 15, "condition": "Rainy"},
    }
    return data.get(city, {"temp": 20, "condition": "Unknown"})


def test_variant_detailed(name, prompt_text):
    """Test with verbose output to analyze behavior"""
    import tinyagent.prompt

    original = tinyagent.prompt.SYSTEM
    tinyagent.prompt.SYSTEM = prompt_text

    results = {"simple_calc": None, "weather": None}

    try:
        # Test 1: Simple calculation
        agent = ReactAgent(tools=[calculator], model="gpt-4o-mini")
        buffer = io.StringIO()
        start = time.time()

        with contextlib.redirect_stdout(buffer):
            answer = agent.run("What is 15% of 200?", max_steps=5, verbose=True)

        output = buffer.getvalue()
        results["simple_calc"] = {
            "success": True,
            "answer": answer,
            "time": time.time() - start,
            "steps": output.count("STEP"),
            "json_errors": output.count("JSON PARSE ERROR"),
            "scratchpad": output.count("[SCRATCHPAD]:"),
        }

        time.sleep(1)

        # Test 2: Weather comparison (multi-step)
        agent = ReactAgent(tools=[get_weather], model="gpt-4o-mini")
        buffer = io.StringIO()
        start = time.time()

        with contextlib.redirect_stdout(buffer):
            answer = agent.run(
                "Which city has better weather, Tokyo or London?", max_steps=5, verbose=True
            )

        output = buffer.getvalue()
        results["weather"] = {
            "success": True,
            "answer": answer[:80] + "..." if len(answer) > 80 else answer,
            "time": time.time() - start,
            "steps": output.count("STEP"),
            "json_errors": output.count("JSON PARSE ERROR"),
            "scratchpad": output.count("[SCRATCHPAD]:"),
        }

    except Exception as e:
        # Fill in error for whichever test failed
        for key in results:
            if results[key] is None:
                results[key] = {"success": False, "error": str(e)[:100]}

    finally:
        tinyagent.prompt.SYSTEM = original

    return results


print("Testing All TinyAgent Prompt Variations")
print("=" * 80)

all_results = {}

# Test each variant
for name, prompt in PROMPT_VARIANTS.items():
    print(f"\n{'=' * 60}")
    print(f"VARIANT: {name}")
    print(f"{'=' * 60}")

    results = test_variant_detailed(name, prompt)
    all_results[name] = results

    # Print results for this variant
    for test_name, result in results.items():
        print(f"\n{test_name}:")
        if result["success"]:
            print(
                f"  ✓ Time: {result['time']:.2f}s, Steps: {result['steps']}, JSON errors: {result['json_errors']}, Scratchpad: {result['scratchpad']}"
            )
            print(f"  Answer: {result.get('answer', 'N/A')}")
        else:
            print(f"  ✗ Error: {result.get('error', 'Unknown error')}")

    time.sleep(1)

# Summary table
print(f"\n{'=' * 80}")
print("COMPARISON SUMMARY")
print(f"{'=' * 80}")
print(
    f"\n{'Variant':<20} {'Success':<10} {'Avg Time':<12} {'Total Steps':<12} {'JSON Errors':<12} {'Scratchpad':<12}"
)
print("-" * 80)

for variant, results in all_results.items():
    successful = [r for r in results.values() if r.get("success")]
    if successful:
        success_rate = len(successful) / len(results)
        avg_time = sum(r["time"] for r in successful) / len(successful)
        total_steps = sum(r["steps"] for r in successful)
        total_errors = sum(r["json_errors"] for r in successful)
        total_scratchpad = sum(r["scratchpad"] for r in successful)

        print(
            f"{variant:<20} {success_rate:<10.0%} {avg_time:<12.2f} {total_steps:<12} {total_errors:<12} {total_scratchpad:<12}"
        )
    else:
        print(f"{variant:<20} {'0%':<10} {'-':<12} {'-':<12} {'-':<12} {'-':<12}")

# Find best performers
if any(all_results.values()):
    variants_with_success = [
        (v, rs) for v, rs in all_results.items() if any(r.get("success") for r in rs.values())
    ]

    if variants_with_success:
        fastest = min(
            variants_with_success,
            key=lambda x: sum(r["time"] for r in x[1].values() if r.get("success"))
            / len([r for r in x[1].values() if r.get("success")]),
        )
        most_reasoning = max(
            variants_with_success,
            key=lambda x: sum(r.get("scratchpad", 0) for r in x[1].values() if r.get("success")),
        )

        print(f"\n🏆 Fastest: {fastest[0]}")
        print(f"🧠 Most reasoning: {most_reasoning[0]}")
