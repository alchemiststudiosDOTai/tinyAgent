#!/usr/bin/env python3
"""Test the current improved prompt"""

from dotenv import load_dotenv

from tinyagent import ReactAgent, tool

load_dotenv()


@tool
def calculator(expression: str) -> float:
    """Evaluate a mathematical expression"""
    return eval(expression)


print("Testing Current Improved Prompt")
print("=" * 60)

# Read current prompt
with open("tinyagent/prompt.py", "r") as f:
    content = f.read()
    if "###Instruction###" in content:
        print("✓ Using new structured prompt with examples")
    else:
        print("✗ Still using old prompt")

# Test queries
queries = [
    "What is 25% of 80?",
    "Calculate 15% tip on $45.50",
    "If I have $100 and spend 30%, how much is left?",
]

agent = ReactAgent(tools=[calculator], model="gpt-4o-mini")

for query in queries:
    print(f"\nQuery: {query}")
    try:
        answer = agent.run(query, max_steps=3, verbose=False)
        print(f"✓ Answer: {answer}")
    except Exception as e:
        print(f"✗ Error: {e}")
