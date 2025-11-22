"""
Web Browse Tool for fetching and converting web pages to markdown

This module provides a web browsing tool that can be used with ReactAgent.
Fetches web pages and converts HTML content to clean markdown format.
"""

import httpx

from tinyagent.core.registry import tool


@tool
async def web_browse(url: str, headers: dict[str, str] | None = None) -> str:
    """Fetch a web page and convert it to markdown format.

    Args:
        url: The URL to fetch
        headers: Optional HTTP headers to include in the request

    Returns:
        String containing the web page content converted to markdown
    """
    try:
        # Import markdownify here to avoid requiring it at import time
        # prob over defensive will update later

        try:
            from markdownify import markdownify as md
        except ImportError:
            return "Error: markdownify library not installed. Run: pip install markdownify"

        # Set default headers if none provided
        if headers is None:
            headers = {}

        # Add a user agent if not provided
        if "User-Agent" not in headers:
            headers["User-Agent"] = "tinyAgent-WebBrowse/1.0"

        # Fetch the web page
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                return f"Error: Failed to fetch URL with status {response.status_code}"

            # Convert HTML to markdown
            markdown_content = md(response.text, heading_style="ATX", strip=["script", "style"])

            if not markdown_content or not markdown_content.strip():
                return "Error: No content found on the page"

            return markdown_content.strip()

    except httpx.RequestError as e:
        return f"Error: Request failed - {str(e)}"
