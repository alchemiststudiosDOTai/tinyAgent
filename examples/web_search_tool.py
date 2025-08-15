"""
Web Search Tool Demo

Example usage of web search tool from tinyagent.base_tools.
Requires BRAVE_SEARCH_API_KEY environment variable.
"""

from tinyagent import ReactAgent
from tinyagent.base_tools import web_search

if __name__ == "__main__":
    # Quick test - direct search
    print("=== Testing Web Search Tool ===")
    results = web_search("FastAPI vs Django 2024")
    print(f"Search results:\n{results}\n")

    # Test with ReactAgent for more complex queries
    agent = ReactAgent(tools=[web_search], model="gpt-4o-mini")

    print("=== Testing with ReactAgent ===")
    answer = agent.run(
        "What are the pros and cons of FastAPI compared to Flask?",
        max_steps=3,
        verbose=False,
    )
    print(f"Agent answer: {answer}")
