#!/usr/bin/env python3
"""
Example 6: Custom Text Browser Demo

This example demonstrates using the custom text browser tool to navigate web content
through the agent framework with proper error handling and output formatting.
"""

from core.tools.custom_text_browser import get_tool
from core.factory.agent_factory import AgentFactory
from core.agent import Agent
import sys
import os
from pathlib import Path

# Add project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))


def main():
    """Create and run an agent with text browser capabilities."""
    print("Custom Text Browser Example")
    print("---------------------------")
    print("This example demonstrates using the custom text browser tool to")
    print("navigate web content through the agent framework.")
    print()

    # Get the singleton factory instance
    factory = AgentFactory.get_instance()

    # Register the text browser tool
    factory.register_tool(get_tool())

    # Create an agent that will use the factory
    agent = Agent(factory=factory)

    # Example operations
    operations = [
        {
            "desc": "Visit a webpage",
            "query": "Use text browser to visit huggingface blog",
            "variables": {
                "action": "visit",
                "path_or_uri": "https://huggingface.co/blog/open-deep-research",
                "use_proxy": False,
                "random_delay": True
            }
        },
        {
            "desc": "Find text on page",
            "query": "Search page for LLM research content",
            "variables": {
                "action": "find",
                "query": "LLM research"
            }
        },
        {
            "desc": "Get page links",
            "query": "Extract all links from the page",
            "variables": {
                "action": "get_links"
            }
        }
    ]

    # Run each operation
    for op in operations:
        print(f"\nOperation: {op['desc']}")
        print(f"Executing: {op['query']}")
        try:
            result = agent.run(op["query"], variables=op["variables"])

            if isinstance(result, dict):
                if result.get("status") == "error":
                    print(f"Operation failed: {result.get('error')}")
                else:
                    print("\nOperation succeeded:")
                    if 'content' in result:
                        content = result['content']
                        preview = content[:500] + \
                            "..." if len(content) > 500 else content
                        print(f"Content Preview:\n{preview}")
                    if 'title' in result:
                        print(f"Page Title: {result['title']}")
                    if 'links' in result:
                        print(f"Found {len(result['links'])} links:")
                        for link in result['links'][:5]:
                            print(f"- {link['text']} ({link['href']})")
            else:
                print("Received unexpected result format:")
                print(result)

        except Exception as e:
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")


if __name__ == "__main__":
    main()
