"""
Web Search Tool Demo

Example usage of web search tools from tinyagent.base_tools.
Requires BRAVE_SEARCH_API_KEY environment variable.
"""

from tinyagent import ReactAgent
from tinyagent.base_tools import search_summary, web_search

if __name__ == "__main__":
    # Quick test - search for Python frameworks
    print("=== Testing Web Search Tool ===")
    summary = search_summary("FastAPI vs Django 2024")
    print(f"Search summary:\n{summary}\n")

    # Test with ReactAgent for more complex queries
    agent = ReactAgent(tools=[web_search, search_summary], model="gpt-4o-mini")

    print("=== Testing with ReactAgent ===")
    answer = agent.run(
        "What are the pros and cons of FastAPI compared to Flask?",
        max_steps=3,
        verbose=False,
    )
    print(f"Agent answer: {answer}")
