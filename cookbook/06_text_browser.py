#!/usr/bin/env python3
"""
Example 6: Text Browser Tool Usage

Demonstrates proper tool usage through the AgentFactory with the updated CustomTextBrowser tool.
"""

import os
import sys
from typing import Dict, Any

# Add parent directory to the path to import core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factory.agent_factory import AgentFactory
from core.factory.orchestrator import Orchestrator
from core.logging import get_logger
from core.cli.colors import Colors

logger = get_logger(__name__)

def format_result(result: Dict[str, Any]) -> str:
    """Format the tool result for display."""
    formatted = []
    formatted.append(f"{Colors.INFO}Page Title:{Colors.OFF_WHITE} {result.get('title', 'No title')}")
    
    if content := result.get('content'):
        limited = (content[:500] + "...") if len(content) > 500 else content
        formatted.append(f"\n{Colors.INFO}Content Preview:{Colors.OFF_WHITE}\n{'-'*50}")
        formatted.append(limited)
        formatted.append("-"*50)
    
    if viewport := result.get('viewport_info'):
        formatted.append(
            f"{Colors.INFO}Viewport:{Colors.OFF_WHITE} "
            f"Page {viewport.get('current', 1)} of {viewport.get('total', 1)}"
        )
    
    if links := result.get('links'):
        formatted.append(f"\n{Colors.INFO}Found {len(links)} links:{Colors.OFF_WHITE}")
        for link in links[:5]:  # Show first 5 links
            formatted.append(f"• {link['text']} ({link['url']})")
    
    return "\n".join(formatted)

def main():
    """Create and run an agent with the text browser tool."""
    # Initialize components
    orchestrator = Orchestrator.get_instance()
    factory = AgentFactory.get_instance()
    
    # Create agent with browser tool
    agent = factory.create_agent(
        tools=["custom_text_browser"],
        model="gpt-4-turbo",
        max_retries=3
    )
    
    # Example URL to visit
    url = "https://huggingface.co/blog/open-deep-research"
    print(f"{Colors.INFO}Using text browser to visit:{Colors.OFF_WHITE} {url}")
    
    try:
        # Execute through agent with proper tool selection
        result = agent.run(
            f"Visit {url} using the custom_text_browser with random_delay=True",
            variables={"random_delay": True}
        )
        
        if result and isinstance(result, dict):
            print(f"\n{format_result(result)}")
        else:
            print(f"{Colors.WARNING}No valid result returned from agent{Colors.OFF_WHITE}")
            
    except Exception as e:
        print(f"{Colors.ERROR}Error:{Colors.OFF_WHITE} {str(e)}")
        logger.error("Example failed", exc_info=True)

if __name__ == "__main__":
    main()
