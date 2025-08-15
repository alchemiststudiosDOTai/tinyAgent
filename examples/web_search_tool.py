"""
Web Search Tool Demo

Example usage of web search tools from tinyagent.base_tools.
Requires BRAVE_SEARCH_API_KEY environment variable.
"""

from tinyagent import ReactAgent
from tinyagent.base_tools import search_summary, web_search

if __name__ == "__main__":
    # Demo usage
    print("Testing web search tool:")
    result = web_search("python web scraping libraries")
    print(
        f"Direct call result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}"
    )

    # Test with ReactAgent (pass functions directly - they're decorated with @tool)
    agent = ReactAgent(tools=[web_search, search_summary], model="gpt-4o-mini")  # type: ignore[arg-type]

    print("\nTesting with ReactAgent:")
    answer = agent.run(
        "Search for information about the latest Python web frameworks and summarize what you find",
        max_steps=5,
        verbose=True,
    )
    print(f"Agent response: {answer}")
