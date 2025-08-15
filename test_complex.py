#!/usr/bin/env python3
"""Test variants with a complex multi-step problem"""

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


# Complex query that requires multiple steps
COMPLEX_QUERY = """Calculate the following:
1. What is 18% of 250?
2. Add 15% to that result
3. Then subtract 25% from the total"""

print("Testing Complex Multi-Step Query")
print("=" * 60)
print(f"Query: {COMPLEX_QUERY}")
print("=" * 60)

for name, prompt in PROMPT_VARIANTS.items():
    print(f"\n{name.upper()}")
    print("-" * 30)

    import tinyagent.prompt

    original = tinyagent.prompt.SYSTEM
    tinyagent.prompt.SYSTEM = prompt

    try:
        agent = ReactAgent(tools=[calculator], model="gpt-4o-mini")
        buffer = io.StringIO()
        start = time.time()

        with contextlib.redirect_stdout(buffer):
            answer = agent.run(COMPLEX_QUERY, max_steps=8, verbose=True)

        elapsed = time.time() - start
        output = buffer.getvalue()

        steps = output.count("STEP")
        tools_used = output.count("[TOOL CALL]:")
        scratchpad = output.count("[SCRATCHPAD]:")

        print(f"✓ Answer: {answer}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Steps: {steps}, Tool calls: {tools_used}, Reasoning: {scratchpad}")

        # Show first scratchpad entry
        if "[SCRATCHPAD]:" in output:
            first_scratch = output.split("[SCRATCHPAD]:")[1].split("\n")[0].strip()
            print(f"  First reasoning: {first_scratch[:80]}...")

    except Exception as e:
        print(f"✗ Failed: {str(e)[:100]}")

    finally:
        tinyagent.prompt.SYSTEM = original

    time.sleep(1)
