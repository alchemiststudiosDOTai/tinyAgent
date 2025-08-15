#!/usr/bin/env python3
"""Quick test of prompt variations"""

import time

from dotenv import load_dotenv

from prompt_variations import PROMPT_VARIANTS
from tinyagent import ReactAgent, tool

load_dotenv()


@tool
def calculator(expression: str) -> float:
    """Evaluate a mathematical expression"""
    return eval(expression)


# Just test one query per variant
def test_variant(name, prompt_text):
    print(f"\n{'=' * 60}")
    print(f"Testing: {name}")
    print(f"Prompt preview: {prompt_text[:100]}...")

    # Monkey patch the prompt
    import tinyagent.prompt

    original = tinyagent.prompt.SYSTEM
    tinyagent.prompt.SYSTEM = prompt_text

    try:
        agent = ReactAgent(tools=[calculator], model="gpt-4o-mini")

        start = time.time()
        # Simple test without verbose to run faster
        answer = agent.run("What is 15% of 200?", max_steps=3, verbose=False)
        elapsed = time.time() - start

        print(f"✓ Success: {answer}")
        print(f"  Time: {elapsed:.2f}s")
        return True, elapsed

    except Exception as e:
        print(f"✗ Error: {e}")
        return False, 0
    finally:
        tinyagent.prompt.SYSTEM = original


# Test only first 3 variants
for i, (name, prompt) in enumerate(PROMPT_VARIANTS.items()):
    if i >= 3:
        break
    success, time_taken = test_variant(name, prompt)
    time.sleep(1)
