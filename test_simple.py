#!/usr/bin/env python3
"""Simple test to show different prompts in action"""

# Load env vars
from dotenv import load_dotenv

from prompt_variations import PROMPT_VARIANTS
from tinyagent import ReactAgent, tool

load_dotenv()


# Simple tool
@tool
def calculator(expression: str) -> float:
    """Evaluate a mathematical expression"""
    return eval(expression)


def test_prompt(name, prompt_text):
    """Test a single prompt and show the interaction"""
    print(f"\n{'=' * 60}")
    print(f"TESTING: {name}")
    print(f"{'=' * 60}")
    print("\nPROMPT PREVIEW:")
    print(prompt_text[:200] + "...")

    # Override prompt
    import tinyagent.prompt as prompt_module

    original = prompt_module.SYSTEM
    prompt_module.SYSTEM = prompt_text

    try:
        agent = ReactAgent(tools=[calculator], model="gpt-4o-mini")

        query = "What is 25% of 80?"
        print(f"\nQUERY: {query}")
        print("\nRUNNING...")

        answer = agent.run(query, max_steps=3, verbose=True)
        print(f"\nFINAL ANSWER: {answer}")

    except Exception as e:
        print(f"\nERROR: {e}")
    finally:
        prompt_module.SYSTEM = original


# Test just a few variants
test_prompt("Original", PROMPT_VARIANTS["original"])
test_prompt("Structured", PROMPT_VARIANTS["structured"])
test_prompt("Chain of Thought", PROMPT_VARIANTS["chain_of_thought"])
