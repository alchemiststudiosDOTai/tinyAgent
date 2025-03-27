
#!/usr/bin/env python3
"""
Example 9: Business Research Agent

Demonstrates using the DuckDuckGo search tool for business research tasks.
"""

from core.tools import duckduckgo_search_tool
from core.logging import get_logger
from core.factory.orchestrator import Orchestrator
from core.factory.agent_factory import AgentFactory
from core.agent import Agent
import os
import sys

# Add parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


logger = get_logger(__name__)


def main():
    """Create and run a business research agent using DuckDuckGo search."""
    # Initialize the orchestrator
    orchestrator = Orchestrator.get_instance()

    # Example business research query
    query = """Research emerging kratom brands
    Find recent news, funding rounds, and key players."""

    print(f"Running business research with query: '{query}'")

    # Submit the task
    task_id = orchestrator.submit_task(query)

    # Get the result
    task_status = orchestrator.get_task_status(task_id)

    # Print formatted results
    print("\nBusiness Research Results:")
    if task_status.result and task_status.result.get('success'):
        for idx, result in enumerate(task_status.result['results'], 1):
            print(f"\nResult {idx}:")
            print(f"Title: {result.get('title', 'No title')}")
            print(f"URL: {result.get('url', 'No URL')}")
            print(f"Snippet: {result.get('snippet', 'No snippet')}")
    else:
        print("Error performing research:",
              task_status.result.get('error', 'Unknown error'))


def business_research_agent(query: str) -> dict:
    """Business research tool implementation using DuckDuckGo search."""
    try:
        # Execute the search tool with business research parameters
        results = duckduckgo_search_tool.execute(
            keywords=query,
            max_results=15,  # Get more results for comprehensive research
            region="us-en",  # Focus on US English results
            safesearch="moderate",
            timelimit="m",  # Last month
            backend="html"  # Use HTML backend for fresher results
        )

        return {
            "success": True,
            "query": query,
            "results": results.get('results', [])
        }
    except Exception as e:
        logger.error(f"Research error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "query": query
        }


if __name__ == "__main__":
    main()
