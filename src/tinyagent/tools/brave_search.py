"""
Brave web search tool for the tinyAgent framework.

This module provides a tool for searching the web using Brave Search API
via MCP integration. It returns structured search results including title,
description, and URL for each result.
"""

from ..exceptions import ToolError
from ..logging import get_logger
from ..tool import ParamType, Tool

# Set up logger
logger = get_logger(__name__)


def brave_web_search(query: str, count: int = 5) -> str:
    """
    Search the web using Brave Search MCP.

    This function leverages the Model Context Protocol (MCP) integration to
    perform web searches using the Brave Search API. It returns structured
    results including titles, descriptions, and URLs.

    Args:
        query: The search query string
        count: Number of results to return (default: 5, max: 20)

    Returns:
        JSON formatted search results

    Raises:
        ToolError: If the MCP server is not running or returns an error
    """
    # Import MCP call function here to avoid circular imports
    from ..mcp import call_mcp_tool

    # Validate inputs
    if not query or not isinstance(query, str):
        raise ToolError("Search query must be a non-empty string")

    if not isinstance(count, int) or count < 1:
        count = 5  # Use default if invalid
    elif count > 20:
        count = 20  # Cap at maximum

    try:
        logger.info(f"Performing Brave web search for: {query} (count: {count})")
        result = call_mcp_tool(
            "brave_web_search", {"query": query, "count": count}, None
        )
        return result
    except Exception as e:
        error_msg = f"Brave Search failed: {str(e)}"
        logger.error(error_msg)
        raise ToolError(error_msg) from e


# Define the tool
brave_web_search_tool = Tool(
    name="brave_web_search",
    description="""
    Search the web using Brave Search to find websites, articles, and information.

    This tool performs web searches using the Brave Search API and returns
    structured results including titles, descriptions, and URLs.

    Examples:
    - Basic search: query="climate change", count=5
    - More results: query="python programming tutorial", count=10

    Note: Requires the Brave API to be configured in the MCP settings.
    """,
    parameters={"query": ParamType.STRING, "count": ParamType.INTEGER},
    manifest={
        "parameters": {
            "query": {
                "type": "string",
                "required": True,
                "description": "The search query string",
            },
            "count": {
                "type": "integer",
                "required": False,
                "default": 5,
                "description": "Number of results to return (default: 5, max: 20)",
            },
        }
    },
    func=brave_web_search,
)


def get_tool() -> Tool:
    """
    Return the brave_web_search tool instance for tinyAgent integration.

    Returns:
        Tool: The brave_web_search tool object
    """
    return brave_web_search_tool
