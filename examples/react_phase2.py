#!/usr/bin/env python3
"""
Reasoning Agent Example - Phase 2: Integration with TinyAgent Framework

This example shows how to use the Reasoning agent with the framework's built-in
LLM and JSON parsing capabilities.
"""

from dotenv import load_dotenv
from tinyagent.reasoning_agent.reasoning_agent import ReasoningAgent
from tinyagent.decorators import tool
from tinyagent.agent import get_llm

# Load environment variables
load_dotenv()


# Create our tools
@tool
def add_numbers(a: float, b: float) -> float:
    """Add two numbers together."""
    result = a + b
    print(f"\n[Tool Execution] add_numbers({a}, {b}) = {result}")
    return result


@tool
def multiply_numbers(a: float, b: float) -> float:
    """Multiply two numbers."""
    result = a * b
    print(f"\n[Tool Execution] multiply_numbers({a}, {b}) = {result}")
    return result


def main():
    print("🚀 Reasoning Agent Example\n")

    # Create the agent
    agent = ReasoningAgent()

    # Register tools
    agent.register_tool(add_numbers._tool)
    agent.register_tool(multiply_numbers._tool)
    print(f"📦 Registered tools: {list(agent.tools.keys())}\n")

    # Get the LLM from the framework
    llm = get_llm()

    # Test queries
    queries = [
        "What is 15 plus 27?",
        "Calculate 8 times 9",
        "I need to add 100 and 250, then multiply the result by 2",
    ]

    # Test the multi-step query to see scratchpad in action
    for query in queries[2:3]:  # Use the complex query
        print(f"\n{'=' * 60}")
        print(f"Query: {query}")
        print(f"{'=' * 60}")

        try:
            result = agent.run_reasoning(
                query=query,
                llm_callable=llm,
                max_steps=5,
                verbose=True,  # Show all steps and scratchpad
            )

            print(f"\n✅ Final answer: {result}")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback

            traceback.print_exc()

    print("\n\n📊 HOW REASONING AGENT WORKS:")
    print("1. User asks a question")
    print("2. Agent THINKS about what to do")
    print("3. Agent takes an ACTION (uses a tool)")
    print("4. Agent OBSERVES the result")
    print("5. Repeat steps 2-4 until answer is found")
    print("6. Agent provides FINAL ANSWER")


if __name__ == "__main__":
    main()

