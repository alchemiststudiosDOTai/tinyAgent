#!/usr/bin/env python3
"""
Example 6: Text Browser Tool Usage

This example demonstrates how to use the custom text browser tool to visit a webpage
and extract limited content.
"""

import os
import sys

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factory.agent_factory import AgentFactory
from core.factory.orchestrator import Orchestrator
from core.logging import get_logger
from core.tools.custom_text_browser import custom_text_browser_tool, custom_text_browser_function

logger = get_logger(__name__)

def main():
    """Create and run an agent with the text browser tool."""
    # Initialize the orchestrator
    orchestrator = Orchestrator.get_instance()
    
    # Get the factory instance
    factory = AgentFactory.get_instance()
    
    # Register the text browser tool with the factory
    factory.register_tool(custom_text_browser_tool)
    
    # Example URL to visit
    url = "https://huggingface.co/blog/open-deep-research"
    print(f"Using text browser to visit: {url}")
    
    # Use the text browser function directly with explicit parameters
    result = custom_text_browser_function(
        url=url,
        action='visit',
        use_proxy=False,
        random_delay=True
    )
    
    # Print the result
    if result:
        # Extract content from the result
        content = result.get('content', '')
        # Limit to 500 characters
        limited_content = content[:500] + "..." if len(content) > 500 else content
        
        print("\nPage Title:", result.get('title', 'No title'))
        print("\nContent (first 500 chars):")
        print("-" * 50)
        print(limited_content)
        print("-" * 50)
        
        # Show viewport information
        viewport_info = result.get('viewport_info', {})
        print(f"\nViewport: Page {viewport_info.get('current', 1)} of {viewport_info.get('total', 1)}")
    else:
        print("No content retrieved")

if __name__ == "__main__":
    main()
