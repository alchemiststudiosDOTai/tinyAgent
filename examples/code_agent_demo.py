#!/usr/bin/env python3
"""
TinyCodeAgent v2 Demo - Showcasing New Features

This example demonstrates the enhanced TinyCodeAgent v2 with:
- Modular execution with resource limits
- Working memory (AgentMemory scratchpad)
- LLM signal primitives (uncertain, explore, commit)
- Trust levels for execution safety
- Enhanced error handling and recovery
"""

import asyncio
import os
import time
from typing import Any

from dotenv import load_dotenv

from tinyagent import ExecutionLimits, TinyCodeAgent, TrustLevel, tool

# Load environment variables from .env file
load_dotenv()


# Example 1: Basic math tools
@tool
def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number recursively."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


@tool
def factorial(n: int) -> int:
    """Calculate n! (n factorial)."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)


# Example 2: Data analysis tools
@tool
def analyze_numbers(numbers: list[int]) -> dict[str, Any]:
    """Analyze a list of numbers and return statistics."""
    if not numbers:
        return {"error": "Empty list provided"}

    sorted_nums = sorted(numbers)
    n = len(sorted_nums)

    # Calculate statistics
    total = sum(sorted_nums)
    mean = total / n

    # Median
    if n % 2 == 0:
        median = (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2
    else:
        median = sorted_nums[n // 2]

    return {
        "count": n,
        "sum": total,
        "mean": mean,
        "median": median,
        "min": sorted_nums[0],
        "max": sorted_nums[-1],
        "range": sorted_nums[-1] - sorted_nums[0],
    }


@tool
def is_prime(n: int) -> bool:
    """Check if a number is prime."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    w = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += w
        w = 6 - w
    return True


# Example 3: String manipulation tools
@tool
def word_stats(text: str) -> dict[str, Any]:
    """Analyze word statistics in a text string."""
    words = text.lower().split()
    word_count = len(words)
    char_count = len(text)

    # Count unique words
    unique_words = set(words)

    # Find longest word
    longest_word = max(words, key=len) if words else ""

    return {
        "word_count": word_count,
        "character_count": char_count,
        "unique_words": len(unique_words),
        "longest_word": longest_word,
        "average_word_length": sum(len(word) for word in words) / word_count
        if word_count > 0
        else 0,
    }


async def demo_basic_usage():
    """Demonstrate basic TinyCodeAgent usage."""
    print("\n" + "=" * 80)
    print("DEMO 1: Basic Mathematical Problem Solving")
    print("=" * 80)

    # Create agent with math tools
    agent = TinyCodeAgent(
        tools=[fibonacci, factorial], model="gpt-4o-mini", extra_imports=["math"], verbose=True
    )

    # Task: Calculate Fibonacci and factorial
    task = "What is the 10th Fibonacci number and 5 factorial? Which one is larger?"

    try:
        result = await agent.run(task)
        print(f"\nANSWER: {result}")
    except Exception as e:
        print(f"\nERROR: {e}")


async def demo_data_analysis():
    """Demonstrate data analysis capabilities."""
    print("\n" + "=" * 80)
    print("DEMO 2: Data Analysis with Statistics")
    print("=" * 80)

    # Create agent with analysis tools
    agent = TinyCodeAgent(tools=[analyze_numbers, is_prime], model="gpt-4o-mini", verbose=True)

    # Task: Analyze numbers and find primes
    task = """Analyze this list of numbers: [12, 7, 23, 45, 89, 2, 17, 34, 67, 91]
    Tell me:
    1. The mean and median
    2. Which numbers are prime
    3. The range of the dataset
    """

    try:
        result = await agent.run(task)
        print(f"\nANSWER: {result}")
    except Exception as e:
        print(f"\nERROR: {e}")


async def demo_advanced_features():
    """Demonstrate advanced v2 features with custom limits."""
    print("\n" + "=" * 80)
    print("DEMO 3: Advanced Features - Memory & Signals")
    print("=" * 80)

    # Create agent with custom limits and all tools
    custom_limits = ExecutionLimits(timeout_seconds=30, max_output_bytes=5000, max_steps=8)

    agent = TinyCodeAgent(
        tools=[analyze_numbers, word_stats, is_prime],
        model="gpt-4o-mini",
        trust_level=TrustLevel.LOCAL,
        limits=custom_limits,
        extra_imports=["random", "string"],
        system_suffix="You have access to memory (scratchpad) and can use uncertain/explore/commit signals.",
        verbose=True,
    )

    # Complex task requiring multi-step reasoning
    task = """Generate 10 random numbers between 1-100, analyze them,
    and create a summary of the findings. Use the scratchpad to keep track
    of your analysis steps. If you're uncertain about any calculation,
    use the uncertain() function.
    """

    try:
        result = await agent.run(task)
        print(f"\nANSWER: {result}")
    except Exception as e:
        print(f"\nERROR: {e}")


async def demo_text_analysis():
    """Demonstrate text analysis capabilities."""
    print("\n" + "=" * 80)
    print("DEMO 4: Text Analysis and Word Statistics")
    print("=" * 80)

    agent = TinyCodeAgent(tools=[word_stats], model="gpt-4o-mini", verbose=True)

    # Text analysis task
    task = """Analyze this famous quote:
    "The only way to do great work is to love what you do. If you haven't found it yet, keep looking. Don't settle."
    Tell me about word count, unique words, longest word, and average word length.
    """

    try:
        result = await agent.run(task)
        print(f"\nANSWER: {result}")
    except Exception as e:
        print(f"\nERROR: {e}")


async def demo_error_recovery():
    """Demonstrate error handling and recovery."""
    print("\n" + "=" * 80)
    print("DEMO 5: Error Recovery and Intelligent Retrying")
    print("=" * 80)

    agent = TinyCodeAgent(tools=[fibonacci, analyze_numbers], model="gpt-4o-mini", verbose=True)

    # Task that might cause initial errors
    task = "Calculate fibonacci(25) and analyze the result. If fibonacci takes too long, use a smaller number."

    try:
        result = await agent.run(task)
        print(f"\nANSWER: {result}")
    except Exception as e:
        print(f"\nERROR: {e}")


async def main():
    """Run all demonstrations."""
    print("Starting TinyCodeAgent v2 Demonstration")
    print("=" * 80)

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Please set OPENAI_API_KEY environment variable")
        return

    start_time = time.time()

    try:
        # Run all demos
        await demo_basic_usage()
        await demo_data_analysis()
        await demo_advanced_features()
        await demo_text_analysis()
        await demo_error_recovery()

        total_time = time.time() - start_time
        print(f"\nAll demos completed in {total_time:.2f} seconds!")

    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
