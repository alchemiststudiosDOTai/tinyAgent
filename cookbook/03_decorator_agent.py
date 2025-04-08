#!/usr/bin/env python3
"""
Example 3: Decorator Agent

This example demonstrates a more concise way to define tools using decorators.
It highlights type hint integration, simplified tool creation syntax, and optional parameters.
"""

import os
import sys

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.decorators import tool
from core.agent import Agent
from core.factory.agent_factory import AgentFactory


def main():
    """
    Demonstrate using decorators to simplify tool creation.
    
    This example shows how @tool decorators make it easier to define tools
    compared to the factory method shown in previous examples.
    """
    # Get the singleton factory instance
    factory = AgentFactory.get_instance()
    
    # Register our decorated tools with the factory
    # The @tool decorator creates Tool objects but we need to register them explicitly
    factory.register_tool(format_text._tool)
    factory.register_tool(reverse_text._tool)
    factory.register_tool(repeat_text._tool)
    factory.register_tool(word_counter._tool)
    
    # Create an agent with our factory
    agent = Agent()

    # Register factory tools with the agent
    for tool_name, tool in factory.list_tools().items():
        if tool_name != "chat":  # Agent adds chat tool automatically
            agent.create_tool(
                name=tool.name,
                description=tool.description,
                func=tool.func,
                parameters=tool.parameters
            )

    # Execute the agent with different queries to demonstrate our decorated tools
    queries = [
        "Format this text: hello world",
        "Reverse this text: python is awesome",
        "Repeat this 3 times: echo",
        "Count the words in: The quick brown fox jumps over the lazy dog"
    ]
    
    for query in queries:
        print(f"\nRunning agent with query: '{query}'")
        try:
            result = agent.run(query)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")


# ---- Tool Definitions ----
# Notice how we don't need to manually create Tool objects or register them
# The @tool decorator automatically handles type conversion and registration

@tool
def format_text(text: str) -> str:
    """
    Format text with proper capitalization and punctuation.
    
    Args:
        text: The text to format
        
    Returns:
        Formatted text with first letter capitalized and a period added
    """
    # Simple formatting: capitalize first letter and add period if missing
    formatted = text.strip().capitalize()
    if not formatted.endswith(('.', '!', '?')):
        formatted += '.'
    return formatted


@tool(rate_limit=5)
def reverse_text(text: str) -> str:
    """
    Reverse the characters in a text string.
    
    Args:
        text: The text to reverse
        
    Returns:
        The reversed text
    
    Note: This tool is rate-limited to 5 calls per session.
    """
    return text[::-1]


@tool
def repeat_text(text: str, count: int = 1) -> str:
    """
    Repeat a text string multiple times.
    
    Args:
        text: The text to repeat
        count: Number of times to repeat (default: 1)
        
    Returns:
        The repeated text string
    """
    # Validate count to prevent excessive repetition
    if count > 10:
        count = 10  # Cap at 10 for safety
    
    return (text + " ") * count


@tool(description="Count the number of words in a text", retry_limit=2)
def word_counter(text: str) -> int:
    """
    Count the number of words in a text.
    
    Args:
        text: The text string to analyze
        
    Returns:
        The number of words in the text
    """
    # Simple word counting by splitting on whitespace
    return len(text.split())


if __name__ == "__main__":
    main()
