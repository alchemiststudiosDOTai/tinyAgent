#!/usr/bin/env python3
"""
Example 6: Custom Text Browser Demo

This example demonstrates using the custom text browser tool to navigate web content
through the agent framework with proper output formatting.
"""

import sys
import os

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tools.custom_text_browser import get_tool
from core.factory.agent_factory import AgentFactory
from core.agent import Agent


def main():
    """Create and run an agent with text browser capabilities."""
    print("Custom Text Browser Example")
    print("---------------------------")
    print("This example demonstrates using the custom text browser tool to")
    print("navigate web content through the agent framework.")
    print()

    # Get the text browser tool
    text_browser_tool = get_tool()

    # Create an agent
    agent = Agent()

    # Register the text browser tool with the agent
    agent.create_tool(
        name=text_browser_tool.name,
        description=text_browser_tool.description,
        func=text_browser_tool.func,
        parameters=text_browser_tool.parameters
    )

    # Visit a webpage
    result = agent.run(
        "Use text browser to visit huggingface blog",
        variables={
            "action": "visit",
            "path_or_uri": "https://huggingface.co/blog/open-deep-research",
            "use_proxy": False,
            "random_delay": True,
        },
    )

    # Print the result
    if result and isinstance(result, dict):
        # Check for error in result
        if result.get("error"):
            print(f"\nError occurred: {result['error']}")
            return

        # Extract content from the result
        content = result.get("content", "")
        # Limit to 500 characters
        limited_content = content[:500] + "..." if len(content) > 500 else content

        print("\nPage Title:", result.get("title", "No title"))
        print("\nContent (first 500 chars):")
        print("-" * 50)
        print(limited_content)
        print("-" * 50)

        # Show viewport information
        viewport_info = result.get("viewport_info", {})
        print(
            f"\nViewport: Page {viewport_info.get('current', 1)} of {viewport_info.get('total', 1)}"
        )
    else:
        print("No content retrieved")


if __name__ == "__main__":
    main()
