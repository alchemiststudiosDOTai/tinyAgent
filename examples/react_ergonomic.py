#!/usr/bin/env python3
"""
ReactAgent Ergonomic Example - Inspired by smolagents API

This example demonstrates the improved ergonomic ReactAgent API that allows
passing tools directly in the constructor, making it cleaner and more intuitive.
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

def test_ergonomic_api():
    """Test the new ergonomic API inspired by smolagents."""
    print("ReactAgent Ergonomic API Example\n")
    print("=" * 60)
    
    # Method 1: Pass tools directly in constructor (smolagents style!)
    print("Method 1: Passing tools directly in constructor")
    agent = ReactAgent(tools=[calculate_percentage, subtract_numbers])
    
    print(f"\nRegistered tools:")
    for tool in agent.tools:
        if tool.name != "final_answer":  # Don't show the built-in tool
            print(f"  - {tool.name}: {tool.description}")
    
    query = "If I have 15 apples and give away 40%, how many do I have left?"
    print(f"\nQuery: {query}\n")
    
    # Use the cleaner .run() method instead of .run_react()
    result = agent.run(query, max_steps=5)
    print(f"\nFINAL ANSWER: {result}")
    
    print("\n" + "=" * 60)
    
    # Method 2: Create agent first, then register tools
    print("\nMethod 2: Register tools after creation")
    agent2 = ReactAgent()
    agent2.register_tool(add_numbers)
    agent2.register_tool(subtract_numbers)
    
    query2 = "What is 25 + 17 - 8?"
    print(f"\nQuery: {query2}\n")
    
    result2 = agent2.run(query2, max_steps=5)
    print(f"\nFINAL ANSWER: {result2}")
    
    print("\n" + "=" * 60)
    
    # Method 3: Mix of Tool objects and decorated functions
    print("\nMethod 3: Mix of different tool types")
    
    # You can also pass Tool objects directly if needed
    tools_list = [
        calculate_percentage,  # Decorated function
        add_numbers._tool,     # Extracted Tool object
        subtract_numbers       # Another decorated function
    ]
    
    agent3 = ReactAgent(tools=tools_list)
    
    query3 = "What is 20% of 50, then add 15?"
    print(f"\nQuery: {query3}\n")
    
    result3 = agent3.run(query3, max_steps=5)
    print(f"\nFINAL ANSWER: {result3}")

def test_no_base_tools():
    """Test disabling base tools (final_answer)."""
    print("\n" + "=" * 60)
    print("Testing with add_base_tools=False")
    print("=" * 60)
    
    # Create agent without the built-in final_answer tool
    agent = ReactAgent(tools=[add_numbers], add_base_tools=False)
    
    print(f"\nRegistered tools (no final_answer):")
    for tool in agent.tools:
        print(f"  - {tool.name}: {tool.description}")
    
    # Note: This might not complete properly without final_answer tool
    # but demonstrates the flexibility

def main():
    print("Demonstrating the new ergonomic ReactAgent API")
    print("Inspired by smolagents: agent = CodeAgent(tools=[...], model=model)")
    print("\n")
    
    test_ergonomic_api()
    test_no_base_tools()

if __name__ == "__main__":
    main()