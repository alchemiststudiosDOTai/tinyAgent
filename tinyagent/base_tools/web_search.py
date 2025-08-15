"""
Web Search Tool using Brave Search API

This module provides a web search tool that can be used with ReactAgent.
Requires BRAVE_SEARCH_API_KEY environment variable.
"""

import os

import requests

from tinyagent.tools import tool


@tool
def web_search(query: str) -> str:
    """Search the web and return a formatted summary of results.

    Args:
        query: The search query string

    Returns:
        String summary of top search results with titles, descriptions, and URLs
    """
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return "Error: BRAVE_SEARCH_API_KEY environment variable not set"

    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "X-Subscription-Token": api_key,
            },
            params={
                "q": query,
                "count": 5,
                "country": "us",
                "search_lang": "en",
            },
            timeout=10,
        )

        if response.status_code != 200:
            return f"Search failed: API request failed with status {response.status_code}"

        data = response.json()

        if "web" not in data or "results" not in data["web"]:
            return "No search results found"

        web_results = data["web"]["results"]
        if not web_results:
            return "No search results found"

        summary_parts = []
        for i, result in enumerate(web_results[:3], 1):
            title = result.get("title", "No title")
            description = result.get("description", "No description")
            url = result.get("url", "")
            summary_parts.append(f"{i}. {title}\n   {description}\n   {url}")

        return "\n\n".join(summary_parts)

    except requests.RequestException as e:
        return f"Search failed: {str(e)}"
