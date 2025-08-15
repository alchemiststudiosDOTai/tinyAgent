"""
Web Search Tools using Brave Search API

This module provides web search tools that can be used with ReactAgent.
Requires BRAVE_SEARCH_API_KEY environment variable.
"""

import os
from typing import Any, Dict

import requests

from tinyagent.tools import tool


@tool
def web_search(query: str, count: int = 10, country: str = "us") -> Dict[str, Any]:
    """Search the web using Brave Search API.

    Args:
        query: The search query string
        count: Number of results to return (default: 10, max: 20)
        country: Country code for results (default: "us")

    Returns:
        Dict containing search results with web results, snippets, and metadata
    """
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return {"error": "BRAVE_SEARCH_API_KEY environment variable not set"}

    if count > 20:
        count = 20

    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "X-Subscription-Token": api_key,
            },
            params={
                "q": query,
                "count": count,
                "country": country,
                "search_lang": "en",
            },
            timeout=10,
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"API request failed with status {response.status_code}: {response.text}"
            }

    except requests.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}


@tool
def search_summary(query: str) -> str:
    """Get a concise summary of web search results.

    Args:
        query: The search query string

    Returns:
        String summary of top search results
    """
    results = web_search(query, count=5)

    if "error" in results:
        return f"Search failed: {results['error']}"

    if "web" not in results or "results" not in results["web"]:
        return "No search results found"

    web_results = results["web"]["results"]
    if not web_results:
        return "No search results found"

    summary_parts = []
    for i, result in enumerate(web_results[:3], 1):
        title = result.get("title", "No title")
        description = result.get("description", "No description")
        url = result.get("url", "")

        summary_parts.append(f"{i}. {title}\n   {description}\n   {url}")

    return "\n\n".join(summary_parts)
