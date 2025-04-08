#!/usr/bin/env python3
"""
Example 4: Dynamic Agent Creation

This example demonstrates dynamic agent creation based on task requirements.
It shows how the framework can analyze tasks and automatically select appropriate
tools for different purposes.
"""

import os
import sys

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factory.dynamic_agent_factory import DynamicAgentFactory
from core.factory.agent_factory import AgentFactory
from core.agent import Agent
from core.decorators import tool


def main():
    """
    Demonstrate dynamic agent creation based on task analysis.
    
    This example shows how the DynamicAgentFactory can create specialized
    agents tailored to different kinds of tasks.
    """



    # Create the dynamic agent factory
    factory = DynamicAgentFactory.get_instance()
    
    # Register a variety of tools for different purposes
    register_text_tools(factory)
    register_math_tools(factory)
    register_utility_tools(factory)
    
    print("Available tools:")
    for tool_name in factory.list_tools().keys():
        if tool_name != "chat":  # Skip built-in chat tool
            print(f"- {tool_name}")
    
    print("\n" + "="*50)
    print("DYNAMIC AGENT DEMONSTRATION")
    print("="*50)
    
    # Example 1: Text processing task
    text_task = "I need to analyze and transform some text data"
    print(f"\nTask 1: '{text_task}'")
    
    # Create a dynamic agent for the text task
    text_agent = factory.create_dynamic_agent(text_task)
    
    # Show which tools were selected
    print("Selected tools for text processing:")
    for tool in text_agent.get_available_tools():
        if tool.name != "chat":  # Skip built-in chat tool
            print(f"- {tool.name}")
    
    # Example 2: Math calculation task
    math_task = "I need to perform some mathematical calculations"
    print(f"\nTask 2: '{math_task}'")
    
    # Create a dynamic agent for the math task
    math_agent = factory.create_dynamic_agent(math_task)
    
    # Show which tools were selected
    print("Selected tools for math calculations:")
    for tool in math_agent.get_available_tools():
        if tool.name != "chat":  # Skip built-in chat tool
            print(f"- {tool.name}")
    
    # Example 3: Mixed task requiring multiple capabilities
    mixed_task = "I need to analyze some text and perform calculations on the results"
    print(f"\nTask 3: '{mixed_task}'")
    
    # Create a dynamic agent for the mixed task
    mixed_agent = factory.create_dynamic_agent(mixed_task)
    
    # Show which tools were selected
    print("Selected tools for mixed task:")
    for tool in mixed_agent.get_available_tools():
        if tool.name != "chat":  # Skip built-in chat tool
            print(f"- {tool.name}")
    
    # Example task execution
    print("\n" + "="*50)
    print("TASK EXECUTION DEMONSTRATION")
    print("="*50)
    
    # Create a simpler agent with just the tools we need for our demo
    demo_factory = AgentFactory()

    # Create the specific tools we need for our demo
    demo_factory.create_tool(
        name="count_words",
        description="Count the number of words in a text",
        func=lambda text: len(text.split())
    )
    
    demo_factory.create_tool(
        name="multiply",
        description="Multiply two numbers",
        func=lambda a, b: a * b
    )
    
    # Execute a specific task with our demo agent
    execution_task = "Count the words in 'The quick brown fox' and multiply by 2"
    print(f"\nExecuting task: '{execution_task}'")
    
    try:
        # To demonstrate the workflow, we'll manually execute the steps
        print("1. Counting words in 'The quick brown fox'...")
        word_count = demo_factory.execute_tool("count_words", text="The quick brown fox")
        print(f"   Word count: {word_count}")
        
        print("2. Multiplying result by 2...")
        final_result = demo_factory.execute_tool("multiply", a=word_count, b=2)
        print(f"   Final result: {final_result}")
        
        print(f"\nResult: The phrase 'The quick brown fox' has {word_count} words. Multiplying by 2 gives us {final_result}.")
    except Exception as e:
        print(f"Error: {e}")


# ---- Tool Registration Functions ----

def register_text_tools(factory):
    """Register a set of text processing tools with the factory."""
    
    @tool
    def count_words(text: str) -> int:
        """Count the number of words in a text."""
        return len(text.split())
    
    @tool
    def count_characters(text: str) -> int:
        """Count the number of characters in a text."""
        return len(text)
    
    @tool
    def to_uppercase(text: str) -> str:
        """Convert text to uppercase."""
        return text.upper()
    
    @tool
    def to_lowercase(text: str) -> str:
        """Convert text to lowercase."""
        return text.lower()
    
    # Explicitly register tools with the factory
    factory.register_tool(count_words._tool)
    factory.register_tool(count_characters._tool)
    factory.register_tool(to_uppercase._tool)
    factory.register_tool(to_lowercase._tool)


def register_math_tools(factory):
    """Register a set of mathematical tools with the factory."""
    
    @tool
    def add(a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    @tool
    def subtract(a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b
    
    @tool
    def multiply(a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b
    
    @tool
    def divide(a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    
    # Explicitly register tools with the factory
    factory.register_tool(add._tool)
    factory.register_tool(subtract._tool)
    factory.register_tool(multiply._tool)
    factory.register_tool(divide._tool)


def register_utility_tools(factory):
    """Register utility tools with the factory."""
    
    @tool
    def combine_results(result1: str, result2: str) -> str:
        """Combine two results into one string."""
        return f"Combined results: {result1} and {result2}"
    
    @tool
    def format_as_json(data: str) -> str:
        """Format data as a JSON-like string."""
        return f"{{ \"result\": \"{data}\" }}"
    
    # Explicitly register tools with the factory
    factory.register_tool(combine_results._tool)
    factory.register_tool(format_as_json._tool)


if __name__ == "__main__":
    main()
