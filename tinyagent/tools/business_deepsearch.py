"""
Business Deep Search Tool for tinyAgent

This module provides a specialized search tool focused on gathering and analyzing
business information. It combines web search capabilities with business-specific
data extraction and structuring.
"""

import json
import re
import time
import os
import random
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
import logging

from ..decorators import tool
from ..logging import get_logger
from ..agent import get_llm
from ..config import load_config
from .file_manipulator import FileManipulator
from ..tool import ParamType, Tool
from .custom_text_browser import CustomTextBrowser
from .duckduckgo_search import perform_duckduckgo_search
from .content_processor import process_content

# Set up logger
logger = get_logger(__name__)

class BusinessDeepSearch:
    """
    A specialized search tool for gathering and analyzing business information.
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        max_steps: Optional[int] = None,
        debug_level: Optional[int] = None,
        rate_limit_delay: float = 2.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        use_proxy: bool = False
    ):
        """
        Initialize the business deep search tool.

        Args:
            model: Optional model name to use for LLM
            max_steps: Optional override for max steps per research phase
            debug_level: Optional override for debug level (0-2)
            rate_limit_delay: Delay between searches in seconds
            max_retries: Maximum number of retries for failed searches
            retry_delay: Delay between retries in seconds
            use_proxy: Enable proxy usage (requires valid proxy env vars)
        """
        self.config = load_config()
        self.use_proxy = use_proxy

        agent_config = self.config.get("agent", {})
        tool_config = self.config.get("business_deepsearch", {})

        self.max_steps = max_steps or tool_config.get("max_steps", 2)
        self.debug_level = (
            debug_level
            if debug_level is not None
            else tool_config.get("debug_level", agent_config.get("debug_level", 0))
        )
        self.model = model or tool_config.get(
            "model", agent_config.get("default_model", "deepseek/deepseek-r1")
        )
        
        # Rate limiting and retry settings
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize components
        self.browser = CustomTextBrowser()
        self.file_manager = FileManipulator()
        self.llm = get_llm(self.model)

        # Business-specific search categories
        self.search_categories = [
            "market size",
            "company profile",
            "industry analysis",
            "competitors",
            "revenue",
            "regulations",
            "market trends",
            "financial data"
        ]

        # Load proxy configuration if enabled
        if self.use_proxy:
            self.proxy_config = self._load_proxy_config()
            if not self.proxy_config["is_valid"]:
                logger.error("Invalid proxy configuration when use_proxy=True")
                print("ERROR: Required proxy environment variables missing:")
                print("- TINYAGENT_PROXY_USERNAME")
                print("- TINYAGENT_PROXY_PASSWORD")
                print("- TINYAGENT_PROXY_COUNTRY (optional, defaults to US)")
                raise ValueError("Invalid proxy configuration with use_proxy=True")
        else:
            self.proxy_config = {"is_valid": False}

        print(f"Using model: {self.model}")
        print(f"Max steps per research phase: {self.max_steps}")
        print(f"Debug level: {self.debug_level}")
        print(f"Rate limit delay: {self.rate_limit_delay}s")
        print(f"Max retries: {self.max_retries}")
        print(f"Retry delay: {self.retry_delay}s")
        print(f"Proxy configured: {self.proxy_config['is_valid']}")

        # Initialize aiohttp session
        self.session = None

    def _load_proxy_config(self) -> Dict[str, Any]:
        """Load proxy config only when use_proxy=True"""
        from dotenv import load_dotenv
        load_dotenv()

        username = os.getenv('TINYAGENT_PROXY_USERNAME')
        password = os.getenv('TINYAGENT_PROXY_PASSWORD')
        country = os.getenv('TINYAGENT_PROXY_COUNTRY', 'US')

        if not username or not password:
            return {"is_valid": False}
            
        return {
            "is_valid": True,
            "url": f"http://customer-{username}-cc-{country}:{password}@pr.oxylabs.io:7777",
            "username": username,
            "country": country
        }

    async def __aenter__(self):
        """Set up async context manager with optional proxy"""
        if self.use_proxy and not self.proxy_config["is_valid"]:
            raise ValueError("Proxy enabled but configuration invalid")
            
        # Create appropriate session based on proxy setting
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html',
                'Accept-Language': 'en-US,en;q=0.5'
            }
        )
        
        if self.use_proxy:
            # Test proxy connection
            try:
                async with self.session.get(
                    "https://ip.oxylabs.io/location",
                    proxy=self.proxy_config["url"],
                    ssl=False
                ) as test_response:
                    if test_response.status != 200:
                        await self.session.close()
                        raise ValueError(f"Proxy test failed: HTTP {test_response.status}")
                    proxy_test = await test_response.json()
                    print(f"Proxy IP: {proxy_test.get('ip', 'unknown')}")
            except Exception as e:
                await self.session.close()
                raise ValueError(f"Proxy connection failed: {str(e)}")

        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up async context manager."""
        if self.session:
            await self.session.close()

    def _debug_print(self, message: str, level: int = 1) -> None:
        """Print a debug message if the current debug level meets or exceeds `level`."""
        if self.debug_level >= level:
            print(message)

    def _truncate_text(self, text: str, limit: int, label: Optional[str] = None) -> str:
        """Truncate text to a given character limit."""
        if len(text) > limit:
            if label:
                self._debug_print(
                    f"Truncating text from {len(text)} to {limit} characters for {label}",
                    level=1
                )
            return text[:limit] + "... [text truncated]"
        return text

    def _llm_call_and_extract_json(
        self,
        prompt: str,
        topic: str = "LLM request"
    ) -> Union[Dict[str, Any], str]:
        """Send a prompt to the LLM and parse out the first JSON block in the response."""
        try:
            self._debug_print(f"Sending prompt to LLM for {topic}...", level=1)
            response = self.llm(prompt)
            self._debug_print(
                f"Received LLM response ({len(response)} characters)", level=2
            )

            # Regex to capture JSON block
            match = re.search(r'({[\s\S]*})', response)
            if not match:
                error_msg = f"No JSON found in LLM response for {topic}"
                self._debug_print(error_msg, level=1)
                return {"error": error_msg, "raw_response": response[:200] + "..."}
            json_str = match.group(1)

            try:
                parsed = json.loads(json_str)
                return parsed
            except json.JSONDecodeError:
                error_msg = f"Failed to parse JSON for {topic}"
                self._debug_print(error_msg, level=1)
                return {"error": error_msg, "raw_response": json_str[:200] + "..."}

        except Exception as exc:
            error_msg = f"Error in LLM call for {topic}: {str(exc)}"
            logger.error(error_msg)
            return error_msg

    def _generate_business_queries(self, search_term: str) -> List[str]:
        """Generate business-focused search queries."""
        queries = []
        for category in self.search_categories:
            queries.append(f"{search_term} {category}")
        return queries

    def _extract_business_data(self, text: str) -> Dict[str, Any]:
        """Extract business-specific data from text using LLM."""
        prompt = (
            "Extract business information from the following text. "
            "Return the results in JSON format with these categories:\n"
            "{\n"
            '"company_info": [{"name": "...", "description": "..."}],\n'
            '"market_data": [{"metric": "...", "value": "...", "source": "..."}],\n'
            '"industry_trends": [{"trend": "...", "source": "..."}],\n'
            '"regulatory_info": [{"regulation": "...", "region": "...", "status": "..."}],\n'
            '"financial_data": [{"metric": "...", "value": "...", "period": "..."}]\n'
            "}\n\n"
            f"TEXT:\n{text}"
        )

        return self._llm_call_and_extract_json(prompt, topic="business data extraction")

    def _save_results(
        self,
        search_term: str,
        raw_results: List[Dict[str, str]],
        processed_data: Dict[str, Any],
        search_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save both raw and processed results to files."""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(
                self.config.get("file_operations", {}).get(
                    "output_dir", "tinyAgent_output"
                ),
                "business_research"
            )
            query_dir = os.path.join(output_dir, f"query_{timestamp}")
            os.makedirs(query_dir, exist_ok=True)
            print(f"Created research directory: {query_dir}")

            results = {
                "success": True,
                "saved_files": [],
                "metadata": {
                    "timestamp": timestamp,
                    "search_term": search_term,
                    "raw_results_count": len(raw_results),
                    "search_state": search_state
                }
            }

            # Save raw results
            raw_path = os.path.join(query_dir, "raw_results.json")
            try:
                with open(raw_path, 'w', encoding='utf-8') as f:
                    json.dump(raw_results, f, indent=2, ensure_ascii=False)
                results["saved_files"].append(raw_path)
                print(f"Saved raw results to: {raw_path}")
            except Exception as exc:
                error_msg = f"Error saving raw results: {str(exc)}"
                logger.error(error_msg)
                print(error_msg)
                results["raw_error"] = error_msg

            # Save processed data
            processed_path = os.path.join(query_dir, "processed_data.json")
            try:
                with open(processed_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_data, f, indent=2, ensure_ascii=False)
                results["saved_files"].append(processed_path)
                print(f"Saved processed data to: {processed_path}")
            except Exception as exc:
                error_msg = f"Error saving processed data: {str(exc)}"
                logger.error(error_msg)
                print(error_msg)
                results["processed_error"] = error_msg

            # Save search state for potential resume
            state_path = os.path.join(query_dir, "search_state.json")
            try:
                with open(state_path, 'w', encoding='utf-8') as f:
                    json.dump(search_state, f, indent=2, ensure_ascii=False)
                results["saved_files"].append(state_path)
                print(f"Saved search state to: {state_path}")
            except Exception as exc:
                error_msg = f"Error saving search state: {str(exc)}"
                logger.error(error_msg)
                print(error_msg)
                results["state_error"] = error_msg

            return results

        except Exception as exc:
            error_msg = f"Error saving results: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

    async def _browser_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Perform a browser-based search."""
        print(f"\nBrowser Search: {query}")
        results = []
        
        # List of search engines to try
        search_urls = [
            f"https://www.google.com/search?q={query}",
            f"https://www.bing.com/search?q={query}"
        ]
        
        for url in search_urls:
            retries = 0
            while retries < self.max_retries:
                try:
                    # Perform the search with proxy
                    async with self.session.get(
                        url,
                        proxy=self.proxy_url,
                        ssl=False
                    ) as response:
                        if response.status == 200:
                            content = await response.text()
                            # Extract search results from HTML content
                            soup = BeautifulSoup(content, 'html.parser')
                            for result in soup.find_all('div', class_=['g', 'b_algo']):
                                title = result.find('h3')
                                link = result.find('a')
                                snippet = result.find('div', class_=['snippet', 'b_snippet'])
                                
                                if title and link:
                                    results.append({
                                        'title': title.get_text(),
                                        'url': link.get('href'),
                                        'snippet': snippet.get_text() if snippet else '',
                                        'source': 'browser'
                                    })
                                    
                                    if len(results) >= max_results:
                                        break
                            # If we got results successfully, break the retry loop
                            break
                        else:
                            raise ValueError(f"HTTP {response.status}")
                            
                except Exception as e:
                    retries += 1
                    error_msg = f"Error visiting {url} (attempt {retries}/{self.max_retries}): {str(e)}"
                    print(error_msg)
                    logger.error(error_msg)
                    
                    if retries >= self.max_retries:
                        logger.error(f"Max retries ({self.max_retries}) reached for {url}")
                        break
                    
                    # Wait before retrying
                    await asyncio.sleep(self.retry_delay)
                    continue
                    
            if len(results) >= max_results:
                break
                
            # Rate limiting between different search engines
            await asyncio.sleep(self.rate_limit_delay)
        
        if not results:
            error_msg = "Browser search failed to retrieve any results after all retries"
            logger.error(error_msg)
            return [{"error": error_msg, "source": "browser"}]
            
        print(f"Browser search found {len(results)} results\n")
        return results

    async def _ddg_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Perform search using DuckDuckGo."""
        try:
            print(f"\nDuckDuckGo Search: {query}")
            
            # Use the same session configuration as browser search
            ddg_url = f"https://html.duckduckgo.com/html/?q={query}"
            retries = 0
            
            while retries < self.max_retries:
                try:
                    async with self.session.get(
                        ddg_url,
                        proxy=self.proxy_url,
                        ssl=False
                    ) as response:
                        if response.status == 200:
                            content = await response.text()
                            soup = BeautifulSoup(content, 'html.parser')
                            results = []
                            
                            # Parse DuckDuckGo HTML results
                            for result in soup.find_all('div', class_='result'):
                                title_elem = result.find('a', class_='result__a')
                                snippet_elem = result.find('a', class_='result__snippet')
                                
                                if title_elem and snippet_elem:
                                    results.append({
                                        'title': title_elem.get_text(),
                                        'url': title_elem.get('href'),
                                        'snippet': snippet_elem.get_text(),
                                        'source': 'duckduckgo'
                                    })
                                    
                                    if len(results) >= max_results:
                                        break
                            
                            print(f"DuckDuckGo search found {len(results)} results")
                            return results
                        else:
                            raise ValueError(f"HTTP {response.status}")
                            
                except Exception as e:
                    retries += 1
                    error_msg = f"Error in DuckDuckGo search (attempt {retries}/{self.max_retries}): {str(e)}"
                    print(error_msg)
                    logger.error(error_msg)
                    
                    if retries >= self.max_retries:
                        logger.error(f"Max retries ({self.max_retries}) reached for DuckDuckGo search")
                        break
                        
                    await asyncio.sleep(self.retry_delay)
            
            return [{"error": "Failed to get results after all retries", "source": "duckduckgo"}]
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {str(e)}")
            return [{"error": str(e), "source": "duckduckgo"}]

    async def _perform_parallel_search(
        self,
        query: str,
        max_results: int = 5
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Perform browser and DuckDuckGo searches in parallel.
        
        Returns:
            Tuple of (browser_results, ddg_results)
        """
        # Run both searches concurrently
        browser_task = asyncio.create_task(self._browser_search(query, max_results))
        ddg_task = asyncio.create_task(self._ddg_search(query, max_results))
        
        # Wait for both to complete
        browser_results, ddg_results = await asyncio.gather(
            browser_task,
            ddg_task,
            return_exceptions=True
        )
        
        # Handle any exceptions
        if isinstance(browser_results, Exception):
            logger.error(f"Browser search failed: {str(browser_results)}")
            browser_results = [{"error": str(browser_results), "source": "browser"}]
            
        if isinstance(ddg_results, Exception):
            logger.error(f"DuckDuckGo search failed: {str(ddg_results)}")
            ddg_results = [{"error": str(ddg_results), "source": "duckduckgo"}]
            
        return browser_results, ddg_results

    async def _process_search_results(
        self,
        browser_results: List[Dict[str, str]],
        ddg_results: List[Dict[str, str]],
        search_term: str
    ) -> Dict[str, Any]:
        """Process and structure search results into business categories."""
        processed_data = {
            "search_term": search_term,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sources": {
                "browser": {
                    "total_results": len(browser_results),
                    "successful_results": len([r for r in browser_results if "error" not in r]),
                    "results": []
                },
                "duckduckgo": {
                    "total_results": len(ddg_results),
                    "successful_results": len([r for r in ddg_results if "error" not in r]),
                    "results": []
                }
            },
            "combined_analysis": {
                "company_info": [],
                "market_data": [],
                "industry_trends": [],
                "regulatory_info": [],
                "financial_data": []
            }
        }

        # Process browser results
        for result in browser_results:
            if "error" not in result:
                extracted = self._extract_business_data(result.get("snippet", ""))
                if isinstance(extracted, dict) and "error" not in extracted:
                    processed_data["sources"]["browser"]["results"].append({
                        "url": result.get("url", ""),
                        "title": result.get("title", ""),
                        "extracted_data": extracted
                    })
                    # Merge into combined analysis
                    for category in processed_data["combined_analysis"].keys():
                        if category in extracted:
                            processed_data["combined_analysis"][category].extend(
                                extracted[category]
                            )

        # Process DuckDuckGo results
        for result in ddg_results:
            if "error" not in result:
                extracted = self._extract_business_data(result.get("snippet", ""))
                if isinstance(extracted, dict) and "error" not in extracted:
                    processed_data["sources"]["duckduckgo"]["results"].append({
                        "url": result.get("url", ""),
                        "title": result.get("title", ""),
                        "extracted_data": extracted
                    })
                    # Merge into combined analysis
                    for category in processed_data["combined_analysis"].keys():
                        if category in extracted:
                            processed_data["combined_analysis"][category].extend(
                                extracted[category]
                            )

        return processed_data

    def _combine_processed_results(self, processed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine multiple processed results into a single analysis."""
        combined = {
            "company_info": [],
            "market_data": [],
            "industry_trends": [],
            "regulatory_info": [],
            "financial_data": []
        }
        
        for result in processed_results:
            if isinstance(result, dict):
                for category in combined.keys():
                    if category in result.get("combined_analysis", {}):
                        combined[category].extend(result["combined_analysis"][category])
        
        # Remove duplicates while preserving order
        for category in combined.keys():
            seen = set()
            deduped = []
            for item in combined[category]:
                item_str = json.dumps(item, sort_keys=True)
                if item_str not in seen:
                    seen.add(item_str)
                    deduped.append(item)
            combined[category] = deduped
            
        return combined

    async def search(
        self,
        query: str,
        max_results: int = 5,
        resume_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform a business-focused search and return structured results.
        
        Args:
            query: The search query string
            max_results: Maximum number of results to return per source
            resume_state: Optional state from a previous search to resume from
            
        Returns:
            Dictionary containing search results and metadata
        """
        print(f"\n=== PERFORMING PARALLEL BUSINESS SEARCH ===")
        print(f"Search term: {query}")
        print(f"Max results per source: {max_results}")
        
        try:
            # Validate proxy configuration first
            if not self.proxy_config["is_valid"]:
                raise ValueError("Invalid proxy configuration")
            
            if not self.session:
                raise ValueError("Session not initialized. Use 'async with' context manager.")
            
            # Test proxy connection again before starting search
            try:
                async with self.session.get("https://ip.oxylabs.io/location", ssl=False) as test_response:
                    if test_response.status != 200:
                        raise ValueError(f"Proxy connection test failed: HTTP {test_response.status}")
                    proxy_test = await test_response.json()
                    print(f"Using proxy IP: {proxy_test.get('ip', 'unknown')}")
            except Exception as e:
                raise ValueError(f"Proxy connection failed before search: {str(e)}")

            # Initialize or resume search state
            search_state = resume_state or {
                "search_term": query,
                "start_time": datetime.now().isoformat(),
                "total_queries": 0,
                "completed_queries": [],
                "failed_queries": [],
                "total_results": 0,
                "errors": []
            }

            # Generate business-focused queries
            queries = self._generate_business_queries(query)
            search_state["total_queries"] = len(queries)
            
            all_results = []
            processed_results = []
            
            for sub_query in queries:
                try:
                    # Skip if this query was already completed in a previous run
                    if sub_query in search_state["completed_queries"]:
                        print(f"Skipping already completed query: {sub_query}")
                        continue
                        
                    # Perform parallel search
                    browser_results, ddg_results = await self._perform_parallel_search(
                        sub_query,
                        max_results
                    )
                    
                    # Check for critical errors in both sources
                    browser_error = next((r for r in browser_results if "error" in r), None)
                    ddg_error = next((r for r in ddg_results if "error" in r), None)
                    
                    if browser_error and ddg_error:
                        error_msg = f"Both search sources failed for query '{sub_query}'"
                        logger.error(error_msg)
                        search_state["errors"].append({
                            "query": sub_query,
                            "browser_error": browser_error.get("error"),
                            "ddg_error": ddg_error.get("error"),
                            "timestamp": datetime.now().isoformat()
                        })
                        search_state["failed_queries"].append(sub_query)
                        continue
                    
                    # Combine results
                    combined_results = []
                    if not browser_error:
                        combined_results.extend(browser_results)
                    if not ddg_error:
                        combined_results.extend(ddg_results)
                    
                    if combined_results:
                        # Process the results
                        processed = await self._process_search_results(
                            browser_results,
                            ddg_results,
                            sub_query
                        )
                        
                        all_results.extend(combined_results)
                        processed_results.append(processed)
                        search_state["completed_queries"].append(sub_query)
                        search_state["total_results"] += len(combined_results)
                    
                except Exception as e:
                    error_msg = f"Error processing query '{sub_query}': {str(e)}"
                    logger.error(error_msg)
                    search_state["errors"].append({
                        "query": sub_query,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
                    search_state["failed_queries"].append(sub_query)
                    continue
                
                # Rate limiting between queries
                await asyncio.sleep(self.rate_limit_delay)
            
            # Check if we got any results at all
            if not all_results:
                raise ValueError("No results found from any source after all retries")
            
            # Save results
            save_results = self._save_results(
                query,
                all_results,
                {
                    "processed_results": processed_results,
                    "combined_analysis": self._combine_processed_results(processed_results)
                },
                search_state
            )
            
            # Return final results
            return {
                "success": True,
                "raw_results": all_results,
                "processed_results": processed_results,
                "search_state": search_state,
                "save_results": save_results
            }
            
        except Exception as e:
            error_msg = f"Critical error in business search: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "search_state": search_state if 'search_state' in locals() else None
            }
        finally:
            print("=== END PARALLEL BUSINESS SEARCH ===\n")

# Create the tool instance for direct usage
business_deepsearch_tool = BusinessDeepSearch()

@tool(
    name="business_deepsearch",
    description="A specialized search tool for gathering and analyzing business information"
)
def business_deepsearch_tool_wrapper(
    query: str,
    max_results: int = 10,
    max_steps: Optional[int] = None,
    resume_state: Optional[Dict[str, Any]] = None,
    use_proxy: bool = False
) -> Dict[str, Any]:
    """
    Business deep search tool with optional proxy support
    
    Args:
        query: The business-related search query
        max_results: Maximum number of results to return per query (default: 10)
        max_steps: Optional maximum number of steps per research phase
        resume_state: Optional state to resume from a previous search
        use_proxy: Enable proxy usage (requires valid proxy env vars)
        
    Returns:
        Dictionary containing search results and metadata
    """
    searcher = BusinessDeepSearch(max_steps=max_steps, use_proxy=use_proxy)
    return searcher.search(query, max_results=max_results, resume_state=resume_state)

# Create a proper Tool instance for the wrapper
business_deepsearch_tool_wrapper._tool = Tool(
    name="business_deepsearch",
    description="A specialized search tool for gathering and analyzing business information",
    parameters={
        "query": ParamType.STRING,
        "max_results": ParamType.INTEGER,
        "max_steps": ParamType.INTEGER
    },
    func=business_deepsearch_tool_wrapper
)

# Export both the class instance and the tool wrapper
__all__ = ['business_deepsearch_tool', 'business_deepsearch_tool_wrapper', 'BusinessDeepSearch'] 
