"""
DuckDuckGo Search Tool

This module provides a simple interface to search the web using DuckDuckGo.
It's designed to work consistently with other tools in the tinyAgent framework
and provides reliable error handling and result formatting.
"""

import logging
import os
from typing import Dict, List, Optional

from dotenv import load_dotenv

from ..tool import ParamType, Tool

# Load environment variables
load_dotenv()

# Set up logger
logger = logging.getLogger(__name__)


def perform_duckduckgo_search(
    keywords: str,
    max_results: int = 10,
    region: str = "wt-wt",
    safesearch: str = "moderate",
    timelimit: Optional[str] = None,
    backend: str = "auto",
) -> List[Dict[str, str]]:
    """
    Performs a web search using DuckDuckGo and returns formatted results.

    This is a direct implementation without decoration, intended for internal use.
    It returns a list of result dictionaries directly rather than a response object.

    Args:
        keywords: Search query string
        max_results: Maximum number of results to return
        region: Region code (e.g., "wt-wt", "us-en")
        safesearch: SafeSearch setting ("on", "moderate", "off")
        timelimit: Time filter ("d" for day, "w" for week, "m" for month, "y" for year)
        backend: Search backend ("auto", "html", "lite")

    Returns:
        List of dictionaries with title, url, and snippet keys
    """
    logger.info("=== PERFORM_DUCKDUCKGO_SEARCH DEBUG ===")
    logger.info(
        f"Search parameters: keywords={keywords}, max_results={max_results}, region={region}, safesearch={safesearch}, timelimit={timelimit}, backend={backend}"
    )

    # Import here to avoid requiring the package at module level
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.error("duckduckgo_search package not installed")
        return [
            {
                "error": "The duckduckgo_search package is not installed. Please install it with: pip install duckduckgo-search"
            }
        ]

    try:
        # Get proxy credentials directly from environment
        username = os.getenv("TINYAGENT_PROXY_USERNAME")
        password = os.getenv("TINYAGENT_PROXY_PASSWORD")
        country = os.getenv("TINYAGENT_PROXY_COUNTRY", "US")

        # Configure proxy if credentials available
        proxies = None
        if all([username, password]):
            try:
                proxy_url = f"http://customer-{username}-cc-{country}:{password}@pr.oxylabs.io:7777"
                masked_url = proxy_url.replace(password, "********")
                logger.info(f"Using proxy: {masked_url}")
                proxies = {"http": proxy_url, "https": proxy_url}
            except Exception as exc:
                logger.error(f"Error configuring proxy: {str(exc)}")
        else:
            logger.info("No proxy credentials found in environment, skipping proxy")

        # Create DDGS instance with proxy if configured
        ddgs = DDGS(proxies=proxies)
        logger.info(f"Searching DuckDuckGo for: {keywords}")

        # Convert parameters to expected types
        try:
            max_results_int = int(max_results)
        except (ValueError, TypeError):
            logger.warning(f"Invalid max_results value: {max_results}, using default")
            max_results_int = 10

        # Perform the search
        raw_results = list(
            ddgs.text(
                keywords=keywords,
                region=region,
                safesearch=safesearch,
                timelimit=timelimit,
                backend=backend,
                max_results=max_results_int,
            )
        )

        # Format the results consistently
        formatted_results = []
        for result in raw_results:
            formatted_results.append(
                {
                    "title": result.get("title", ""),
                    "href": result.get("href", ""),  # Changed from 'url'
                    "body": result.get("body", ""),  # Changed from 'snippet'
                }
            )

        logger.info(f"Found {len(formatted_results)} results")
        logger.info("=== END PERFORM_DUCKDUCKGO_SEARCH DEBUG ===")

        return formatted_results

    except Exception as e:
        error_msg = f"Error during search: {str(e)}"
        logger.error(error_msg)
        logger.error(f"ERROR: {error_msg}")
        logger.info("=== END PERFORM_DUCKDUCKGO_SEARCH DEBUG ===")
        return [{"error": error_msg}]


# Create the tool instance directly with standard naming
duckduckgo_search_tool = Tool(
    name="duckduckgo_search",
    description="""Search the web using DuckDuckGo and get formatted results.

This tool performs a text search using DuckDuckGo's search engine and returns
formatted results with titles, URLs, and snippets.""",
    parameters={
        "keywords": ParamType.STRING,
        "max_results": ParamType.INTEGER,
        "region": ParamType.STRING,
        "safesearch": ParamType.STRING,
        "timelimit": ParamType.STRING,
        "backend": ParamType.STRING,
    },
    func=lambda **kwargs: {
        "success": True,
        "results": perform_duckduckgo_search(
            keywords=kwargs.get("keywords", ""),
            max_results=kwargs.get("max_results", 10),
            region=kwargs.get("region", "wt-wt"),
            safesearch=kwargs.get("safesearch", "moderate"),
            timelimit=kwargs.get("timelimit"),
            backend=kwargs.get("backend", "auto"),
        ),
    },
)


def get_tool() -> Tool:
    """Return the DuckDuckGo search tool instance"""
    return duckduckgo_search_tool


__all__ = ["duckduckgo_search_tool", "get_tool"]
