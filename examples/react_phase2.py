#!/usr/bin/env python3
"""
ReactAgent Example - README Demo

This example demonstrates the ReactAgent with the same tools and query
used in the README, showing multi-step reasoning with atomic tools.
"""

from tinyagent import tool, ReactAgent

# Create atomic tools following tinyAgent philosophy
@tool
def calculate_percentage(value: float, percentage: float) -> float:
    """Calculate what percentage of a value is (e.g., 40% of 15)."""
    result = value * (percentage / 100)
    print(f"\n[Tool Execution] calculate_percentage({value}, {percentage}%) = {result}")
    return result

@tool
def subtract_numbers(number1: float, number2: float) -> float:
    """Subtract the second number from the first number. Use parameters: number1 (first number), number2 (second number). Returns number1 - number2."""
    result = number1 - number2
    print(f"\n[Tool Execution] subtract_numbers({number1} - {number2}) = {result}")
    return result

@tool
def add_numbers(number1: float, number2: float) -> float:
    """Add two numbers together. Use parameters: number1 (first number), number2 (second number). Returns number1 + number2."""
    result = number1 + number2
    print(f"\n[Tool Execution] add_numbers({number1} + {number2}) = {result}")
    return result

def test_apple_question():
    print("ReactAgent README Example - Apple Calculation\n")
    print("This demonstrates the exact example from the README:")
    print("'If I have 15 apples and give away 40%, how many do I have left?'\n")
    
    # Create ReactAgent with tools passed directly (cleaner API!)
    agent = ReactAgent(tools=[calculate_percentage, subtract_numbers])
    
    print(f"Registered tools:")
    for tool in agent.tools:
        print(f"  - {tool.name}: {tool.description}")
    print()
    
    # The exact query from the README
    query = "If I have 15 apples and give away 40%, how many do I have left?"
    
    print(f"Query: {query}\n")
    print("Starting ReactAgent reasoning process...\n")
    print("="*60)
    
    try:
        # Run with reasoning steps (using cleaner .run() method)
        result = agent.run(query, max_steps=5)
        
        print("="*60)
        print(f"\nFINAL ANSWER: {result}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

def test_math_question():
    print("\n" + "="*80)
    print("Testing with a different math question...")
    print("="*80)
    
    # Create ReactAgent with tools (cleaner API!)
    agent = ReactAgent(tools=[add_numbers, subtract_numbers])
    
    query = "What is 25 + 17 - 8?"
    
    print(f"Query: {query}\n")
    print("Starting ReactAgent reasoning process...\n")
    print("="*60)
    
    try:
        result = agent.run(query, max_steps=5)
        
        print("="*60)
        print(f"\nFINAL ANSWER: {result}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

def main():
    # Test the original apple question
    test_apple_question()
    
    # Test a different type of question
    test_math_question()

if __name__ == "__main__":
    main()