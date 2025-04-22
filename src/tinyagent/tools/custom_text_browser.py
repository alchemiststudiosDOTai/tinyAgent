"""

Custom Text Browser Tool for tinyAgent

This module implements a text-based browser designed specifically for navigating,
viewing, and searching web content. It's intended to be used with the OSDepthSearch
agent to provide enhanced web content exploration capabilities.
Inspired by smolagents and the HF research paper on research agents, I added a few more features from my web scraping background that
Will break this up into a few different tools in the future
https://huggingface.co/blog/open-deep-research
"""

import os
import re
import time
import uuid
import random
from typing import Dict, Any, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from ..decorators import tool
from ..logging import get_logger
from ..tool import ParamType, Tool, ToolError
from ..config import load_config, get_config_value

# Load environment variables
load_dotenv()

# Set up logger
logger = get_logger(__name__)

#  user-agent pool (extend this list with more real user-agents as needed)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/14.0 Mobile/15A5341f Safari/604.1",
]

def get_random_user_agent() -> str:
    """Returns a randomly chosen User-Agent from the predefined list."""
    return random.choice(USER_AGENTS)

class CustomTextBrowser:
    """
    A text-based browser for navigating, viewing, and searching web content.
    
    This version includes:
    - Connection pooling
    - Randomized headers (including a rotating User-Agent)
    - Optional concurrency for batch fetching
    - Randomized (optional) delays between requests
    - Proxy configuration
    """
    
    def __init__(
        self,
        viewport_size: int = 8192,
        downloads_folder: str = "./downloads",
        use_proxy: Optional[bool] = None,
        max_retries: Optional[int] = None,
        backoff_factor: float = 1.0,
        pool_connections: int = 10,
        pool_maxsize: int = 10,
        random_delay_range: Optional[Tuple[float, float]] = (0.5, 2.0),
    ):
        # Load config first
        config = load_config()
        
        # Check global proxy setting first
        proxy_enabled = get_config_value(config, "proxy.enabled", False)
        
        # Only check specific browser proxy setting if global proxy is enabled
        browser_proxy = get_config_value(config, "tools.browser.use_proxy", False) if proxy_enabled else False
        
        # Final proxy setting: explicit parameter > browser config > global config > False
        self._use_proxy = use_proxy if use_proxy is not None else browser_proxy
        
        self._max_retries = max_retries if max_retries is not None else get_config_value(
            config, "tools.browser.max_retries", 3
        )
        """
        Initialize the text browser with enhanced scraping capabilities.
        
        Args:
            viewport_size: Size of viewport in characters (default: 8192)
            downloads_folder: Folder to save downloaded files (default: "./downloads")
            use_proxy: Whether to use proxy configuration from config file (default: True)
            max_retries: Number of retries for failed requests (default: 3)
            backoff_factor: Factor for exponential backoff between retry attempts (default: 1.0)
            pool_connections: Maximum number of connection pools (default: 10)
            pool_maxsize: Maximum number of connections in each pool (default: 10)
            random_delay_range: (min_delay, max_delay) for random sleep before requests, 
                                or None to disable (default: 0.5-2.0 seconds)
        """
        self.viewport_size = viewport_size
        self.downloads_folder = downloads_folder
        os.makedirs(self.downloads_folder, exist_ok=True)
        
        # Browser state
        self.history: List[Tuple[str, float]] = []
        self.current_address: str = "about:blank"
        self.page_title: Optional[str] = None
        self.current_content: str = ""
        
        # Viewport management
        self.viewport_pages: List[Tuple[int, int]] = []
        self.viewport_current_page: int = 0
        
        # Search state
        self._find_query: Optional[str] = None
        self._find_last_result: Optional[int] = None
        
        # Proxy configuration usage
        self._use_proxy = use_proxy
        
        # Random delay range for requests
        self.random_delay_range = random_delay_range
        
        # Create a session with custom headers
        self.session = requests.Session()
        # Use a random User-Agent initially
        self.session.headers.update({
            "User-Agent": get_random_user_agent(),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
                      "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        })
        
        # Configure retries and connection pooling
        retries = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Configure proxy if requested
        if self._use_proxy:
            self._configure_proxy()  # This now includes connection test
        
        # If proxy failed but was requested, disable it
        if self._use_proxy and not self.session.proxies:
            logger.warning("Proxy configuration failed - continuing without proxy")
            self._use_proxy = False

    def _configure_proxy(self):
        """Configure proxy settings with connection verification."""
        try:
            logger.debug("Loading proxy configuration from environment...")
            
            # Get credentials directly from environment like OSS.PY
            username = os.getenv('TINYAGENT_PROXY_USERNAME')
            password = os.getenv('TINYAGENT_PROXY_PASSWORD')
            country = os.getenv('TINYAGENT_PROXY_COUNTRY', 'US')

            if not all([username, password]):
                logger.error("Missing required proxy credentials in environment")
                return
                
            formatted_proxy = f'http://customer-{username}-cc-{country}:{password}@pr.oxylabs.io:7777'
            logger.debug(f"Formatted proxy URL: {formatted_proxy.replace(password, '[REDACTED]')}")

            # Test proxy connection
            test_url = "https://ip.oxylabs.io/location"
            try:
                test_proxies = {
                    "http": formatted_proxy,
                    "https": formatted_proxy
                }
                response = requests.get(
                    test_url, 
                    proxies=test_proxies,
                    timeout=10
                )
                response.raise_for_status()
                logger.info("Proxy connection verified successfully")
            except Exception as test_error:
                logger.error(f"Proxy connection test failed: {str(test_error)}")
                logger.info("Falling back to direct connection")
                self.session.proxies = {}
                return

            # Apply verified proxy to session
            self.session.proxies = test_proxies

        except Exception as e:
            logger.error(f"Error configuring proxy: {str(e)}")
            logger.debug("Proxy configuration failed", exc_info=True)

    @property
    def use_proxy(self) -> bool:
        """Get the current proxy usage setting."""
        return self._use_proxy
        
    @use_proxy.setter
    def use_proxy(self, value: bool):
        """
        Set whether to use proxy configuration.
        
        Args:
            value: True to use proxy, False to disable
        """
        # If value changed
        if self._use_proxy != value:
            self._use_proxy = value
            
            if value:
                # Enable proxy
                self._configure_proxy()
            else:
                # Disable proxy
                self.session.proxies = {}
                logger.info("Proxy disabled for browser")

    def set_address(self, uri_or_path: str) -> None:
        """
        Navigate to a new address and load its content.
        
        Args:
            uri_or_path: URL or path to visit
        """
        self.history.append((uri_or_path, time.time()))
        
        # Possibly sleep randomly to mimic real user traffic
        self._maybe_random_delay()
        # Rotate the User-Agent to reduce blocking
        self._rotate_user_agent()
        
        if uri_or_path == "about:blank":
            self._set_page_content("")
        elif uri_or_path.startswith("http:") or uri_or_path.startswith("https:"):
            self._fetch_page(uri_or_path)
        else:
            # Handle relative URLs
            if len(self.history) > 1:
                prior_address = self.history[-2][0]
                uri_or_path = urljoin(prior_address, uri_or_path)
                self._fetch_page(uri_or_path)
            else:
                # Can't resolve relative URL without history
                self._set_page_content(f"Error: Can't resolve relative URL {uri_or_path} without history")
                
        self.viewport_current_page = 0
        self._find_query = None
        self._find_last_result = None

    def visit_page(self, path_or_uri: str) -> str:
        """
        Visit a page and return the current viewport content.
        
        Args:
            path_or_uri: URL or path to visit
            
        Returns:
            Content of the current viewport
        """
        self.set_address(path_or_uri)
        return self.viewport

    def page_down(self) -> None:
        """Move to the next viewport (scroll down)."""
        if self.viewport_current_page < len(self.viewport_pages) - 1:
            self.viewport_current_page += 1

    def page_up(self) -> None:
        """Move to the previous viewport (scroll up)."""
        if self.viewport_current_page > 0:
            self.viewport_current_page -= 1

    def find_on_page(self, query: str) -> Optional[str]:
        """
        Search for text on the page, starting from the current viewport.
        
        Args:
            query: Text to find (wildcards supported with *)
            
        Returns:
            Viewport content if found, else None
        """
        if not query:
            return None
            
        # Convert query to regex pattern (e.g., "te*t" becomes "te.*t")
        nquery = re.sub(r"\*", ".*", re.escape(query)).lower()
        
        # Search from current position to end
        for i in range(self.viewport_current_page, len(self.viewport_pages)):
            if self._search_in_viewport(i, nquery):
                self.viewport_current_page = i
                self._find_query = query
                self._find_last_result = i
                return self.viewport
                
        # Loop back to the start if not found
        for i in range(0, self.viewport_current_page):
            if self._search_in_viewport(i, nquery):
                self.viewport_current_page = i
                self._find_query = query
                self._find_last_result = i
                return self.viewport
                
        return None

    def find_next(self) -> Optional[str]:
        """
        Find the next match for the current search query.
        
        Returns:
            Viewport content if found, else None
        """
        if not self._find_query:
            return None
            
        nquery = re.sub(r"\*", ".*", re.escape(self._find_query)).lower()
        start = (self._find_last_result + 1) % len(self.viewport_pages) if self._find_last_result is not None else 0
        
        # Search from next position to end
        for i in range(start, len(self.viewport_pages)):
            if self._search_in_viewport(i, nquery):
                self.viewport_current_page = i
                self._find_last_result = i
                return self.viewport
                
        # Loop back to the start
        for i in range(0, start):
            if self._search_in_viewport(i, nquery):
                self.viewport_current_page = i
                self._find_last_result = i
                return self.viewport
                
        return None

    def _search_in_viewport(self, viewport_index: int, nquery: str) -> bool:
        """
        Check if the query matches in a specific viewport.
        
        Args:
            viewport_index: Index of viewport to search
            nquery: Regex query to search for
            
        Returns:
            True if query found in viewport
        """
        start, end = self.viewport_pages[viewport_index]
        content = self.current_content[start:end].lower()
        return bool(re.search(nquery, content))

    def _fetch_page(self, url: str) -> None:
        """
        Fetch content from a URL and process it.
        
        Args:
            url: URL to fetch
        """
        try:
            logger.info(f"Fetching page: {url}")
            
            # Add timeout and retry logic for more robust fetching
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Add proxy awareness to error messages
                    if self._use_proxy:
                        logger.debug(f"Using proxy: {self.session.proxies['https']}")
                    
                    response = self.session.get(url, timeout=15)
                    response.raise_for_status()
                    break
                except requests.exceptions.ProxyError as pe:
                    logger.error(f"Proxy error: {str(pe)}")
                    if retry_count < max_retries - 1:
                        logger.info("Reconfiguring proxy before retry...")
                        self._configure_proxy()  # Re-check proxy config
                    raise
                except (requests.exceptions.ConnectTimeout, 
                        requests.exceptions.ReadTimeout,
                        requests.exceptions.ConnectionError) as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise
                    logger.warning(f"Retry {retry_count}/{max_retries} for {url}: {str(e)}")
                    time.sleep(1)
            
            content_type = response.headers.get("content-type", "")
            
            if "text/html" in content_type:
                # Process HTML content
                soup = BeautifulSoup(response.text, "lxml")
                
                # Extract title
                self.page_title = soup.title.string if soup.title else "Untitled"
                
                # Remove script, style, and other non-content elements
                for tag in soup(["script", "style", "meta", "link", "noscript", "iframe"]):
                    tag.decompose()
                
                # Convert HTML to readable text
                content = self._html_to_text(soup)
                self._set_page_content(content)
                
            else:
                # Handle non-HTML content (download file)
                self._download_file(url, response)
                
            self.current_address = url
            
        except Exception as e:
            logger.error(f"Error fetching page: {str(e)}")
            self.page_title = "Error"
            self._set_page_content(f"Error fetching page: {str(e)}")
            self.current_address = url

    def _html_to_text(self, soup: BeautifulSoup) -> str:
        """
        Convert HTML to readable text.
        
        Args:
            soup: BeautifulSoup object of HTML
            
        Returns:
            Readable text version of HTML
        """
        # Extract and format main content
        content = []
        
        # Add title
        if soup.title:
            content.append(f"# {soup.title.string.strip()}\n")
        
        # Process headings
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                text = heading.get_text().strip()
                if text:
                    content.append(f"{'#' * i} {text}\n")
        
        # Process paragraphs
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if text:
                content.append(f"{text}\n")
        
        # Process lists
        for ul in soup.find_all(['ul', 'ol']):
            for li in ul.find_all('li'):
                text = li.get_text().strip()
                if text:
                    content.append(f"- {text}\n")
        
        # Process links
        for a in soup.find_all('a'):
            href = a.get('href')
            text = a.get_text().strip()
            if href and text:
                # Store links at the end
                content.append(f"[{text}]({href})\n")
        
        return "\n".join(content)

    def _download_file(self, url: str, response: requests.Response) -> None:
        """
        Download non-HTML content and update page content.
        
        Args:
            url: URL of the file
            response: Response object with file content
        """
        try:
            # Create a valid filename from the URL
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                # Generate unique filename if URL doesn't provide one
                content_type = response.headers.get("content-type", "")
                ext = self._get_extension_from_content_type(content_type)
                filename = f"download_{uuid.uuid4()}{ext}"
            
            # Sanitize filename
            filename = self._sanitize_filename(filename)
            
            # Save file
            file_path = os.path.join(self.downloads_folder, filename)
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.page_title = "Download Complete"
            self._set_page_content(f"File downloaded to: {file_path}")
            logger.info(f"Downloaded file to: {file_path}")
            
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            self.page_title = "Download Error"
            self._set_page_content(f"Error downloading file: {str(e)}")

    def _get_extension_from_content_type(self, content_type: str) -> str:
        """
        Get file extension from content type.
        
        Args:
            content_type: HTTP content type
            
        Returns:
            File extension including the dot
        """
        # Common MIME types to extensions mapping
        mime_map = {
            'application/pdf': '.pdf',
            'application/zip': '.zip',
            'application/json': '.json',
            'application/xml': '.xml',
            'text/csv': '.csv',
            'text/plain': '.txt',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif'
        }
        
        # Extract base content type
        base_type = content_type.split(';')[0].strip().lower()
        
        # Return mapped extension or default
        return mime_map.get(base_type, '.bin')

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
        if exc_type is not None:
            logger.error(f"Browser error: {exc_val}", exc_info=True)
        return False  # Don't suppress exceptions

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to be safe for the filesystem.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Replace invalid characters
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 255:
            base, ext = os.path.splitext(filename)
            filename = base[:255-len(ext)] + ext
            
        return filename

    def _set_page_content(self, content: str) -> None:
        """
        Set the page content and split it into viewports.
        
        Args:
            content: Page content
        """
        self.current_content = content
        self._split_pages()

    def _split_pages(self) -> None:
        """Divide the content into viewports based on viewport_size."""
        if not self.current_content:
            self.viewport_pages = [(0, 0)]
            return
            
        self.viewport_pages = []
        start_idx = 0
        
        while start_idx < len(self.current_content):
            # Calculate end index
            end_idx = min(start_idx + self.viewport_size, len(self.current_content))
            
            # Try to end at a line break if possible
            if end_idx < len(self.current_content):
                # First try to find a nearby line break
                line_break = self.current_content.rfind('\n', start_idx, end_idx)
                
                if line_break > start_idx + self.viewport_size // 2:
                    # If we found a line break in the second half of the viewport, use it
                    end_idx = line_break + 1
                else:
                    # Otherwise, find the next word boundary
                    while end_idx < len(self.current_content) and not self.current_content[end_idx-1].isspace():
                        end_idx += 1
            
            self.viewport_pages.append((start_idx, end_idx))
            start_idx = end_idx

    def get_state(self) -> Dict[str, Any]:
        """
        Get the current state of the browser.
        
        Returns:
            Dictionary with browser state information
        """
        return {
            "address": self.current_address,
            "title": self.page_title,
            "viewport_position": {
                "current": self.viewport_current_page + 1 if self.viewport_pages else 0,
                "total": len(self.viewport_pages)
            },
            "content_length": len(self.current_content),
            "viewport": self.viewport
        }

    def get_links(self) -> List[Dict[str, str]]:
        """
        Extract links from current content.
        
        Returns:
            List of dictionaries with link text and URLs
        """
        links = []
        link_pattern = r'\[(.*?)\]\((.*?)\)'
        
        for match in re.finditer(link_pattern, self.current_content):
            text, url = match.groups()
            links.append({"text": text, "url": url})
            
        return links

    @property
    def viewport(self) -> str:
        """
        Get the content of the current viewport.
        
        Returns:
            Content of current viewport
        """
        if not self.viewport_pages:
            return ""
            
        start, end = self.viewport_pages[self.viewport_current_page]
        return self.current_content[start:end]

    def _rotate_user_agent(self):
        """
        Replace the current User-Agent with a new random one 
        to reduce the chance of being blocked.
        """
        ua = get_random_user_agent()
        self.session.headers.update({"User-Agent": ua})
        logger.debug(f"Rotated User-Agent to: {ua}")

    def _maybe_random_delay(self):
        """
        Sleep for a random amount of time if random_delay_range is set.
        """
        if self.random_delay_range is not None:
            delay = random.uniform(*self.random_delay_range)
            logger.debug(f"Sleeping for {delay:.2f} seconds before next request...")
            time.sleep(delay)

    # -------------------------------------------------------------------------
    # Concurrency / Bulk Fetching
    # -------------------------------------------------------------------------
    async def async_fetch(self, url: str) -> str:
        """Asynchronous version of page fetching using aiohttp"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.text()
        except Exception as e:
            raise ToolError(f"Async fetch failed for {url}: {str(e)}") from e

    def fetch_pages_in_parallel(
        self, 
        urls: List[str], 
        concurrency: int = 5,
        timeout: int = 15,
    ) -> Dict[str, Union[str, Exception]]:
        """
        Fetch multiple URLs in parallel using ThreadPoolExecutor.
        Randomization rules (UA rotation / random delays) apply before each request.
        
        Args:
            urls: List of URLs to fetch
            concurrency: Number of threads to use
            timeout: Request timeout in seconds
            
        Returns:
            A dict of {url: content_or_exception}
        """
        results = {}

        def fetch_one(url: str) -> Tuple[str, Union[str, Exception]]:
            try:
                # Possibly delay and rotate agent for each request
                self._maybe_random_delay()
                self._rotate_user_agent()

                resp = self.session.get(url, timeout=timeout)
                resp.raise_for_status()
                content_type = resp.headers.get('content-type', '')
                logger.info(f"URL: {url}, Content-Type: {content_type}")
                
                # Only return text for HTML/text content types
                if 'text/html' in content_type:
                    # Parse HTML and extract readable text
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    # Get text and clean it up
                    text = soup.get_text(separator='\n', strip=True)
                    # Remove excessive newlines
                    text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
                    return (url, text)
                elif 'text/plain' in content_type:
                    return (url, resp.text)
                else:
                    return (url, f"[Content type not supported: {content_type}]")
            except Exception as exc:
                return (url, exc)
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {executor.submit(fetch_one, url): url for url in urls}
            for future in as_completed(futures):
                url = futures[future]
                try:
                    url, content = future.result()
                    results[url] = content
                except Exception as exc:
                    # If something unexpected happened in fetch_one
                    results[url] = exc
        
        return results


def custom_text_browser_function(**kwargs):
    """
    Text browser function implementation that handles different actions.
    """
    action = kwargs.get('action', 'visit')
    
    # Validate required parameters based on action
    if action == 'fetch_parallel':
        urls_str = kwargs.get('urls', "")
        if not urls_str:
            raise ValueError("urls parameter is required for fetch_parallel action")
    else:
        url = kwargs.get('url')
        if not url:
            raise ValueError("url parameter is required for non-parallel actions")
        
    # Initialize browser with configuration
    use_proxy = kwargs.get('use_proxy', False)  # Default to False instead of True
    random_delay = kwargs.get('random_delay', True)
    random_delay_range = (0.5, 2.0) if random_delay else None
    max_retries = kwargs.get('max_retries', 3)
    
    browser = CustomTextBrowser(
        use_proxy=use_proxy,
        random_delay_range=random_delay_range,
        max_retries=max_retries,
        pool_connections=kwargs.get('pool_connections', 10),
        pool_maxsize=kwargs.get('pool_maxsize', 10),
    )
    
    # Handle parallel fetching
    if action == 'fetch_parallel':
        # Convert comma-separated string to list
        urls_str = kwargs.get('urls', "")
        urls = [u.strip() for u in urls_str.split(",") if u.strip()]
        
        if not urls:
            raise ValueError("urls parameter must be a comma-separated list of URLs")
        
        concurrency = kwargs.get('concurrency', 5)
        timeout = kwargs.get('timeout', 15)
        
        results = browser.fetch_pages_in_parallel(
            urls=urls, 
            concurrency=concurrency,
            timeout=timeout
        )
        
        # Format results for response
        formatted_results = {}
        for url, content in results.items():
            if isinstance(content, Exception):
                formatted_results[url] = f"Error: {str(content)}"
            else:
                # Only return a preview of the content to avoid large responses
                preview = content[:500] + "..." if len(content) > 500 else content
                formatted_results[url] = preview
                
        return {
            'action': 'fetch_parallel',
            'urls_processed': len(urls),
            'successful': sum(1 for c in results.values() if not isinstance(c, Exception)),
            'failed': sum(1 for c in results.values() if isinstance(c, Exception)),
            'results': formatted_results
        }
    
    # Standard actions that work with a single page
    if action == 'visit':
        content = browser.visit_page(url)
        return {
            'url': url,
            'action': action,
            'title': browser.page_title,
            'content': content,
            'viewport_info': {
                'current': browser.viewport_current_page + 1,
                'total': len(browser.viewport_pages)
            }
        }
    
    elif action == 'search':
        search_query = kwargs.get('search_query')
        if not search_query:
            raise ValueError("search_query is required for search action")
        
        browser.visit_page(url)
        found = browser.find_on_page(search_query)
        
        return {
            'url': url,
            'action': action,
            'search_query': search_query,
            'found': bool(found),
            'content': found if found else "Search term not found",
            'viewport_info': {
                'current': browser.viewport_current_page + 1,
                'total': len(browser.viewport_pages)
            }
        }
    
    elif action == 'links':
        browser.visit_page(url)
        links = browser.get_links()
        
        return {
            'url': url,
            'action': action,
            'links_count': len(links),
            'links': links
        }
    
    elif action == 'next_page':
        browser.visit_page(url)
        browser.page_down()
        
        return {
            'url': url,
            'action': action,
            'content': browser.viewport,
            'viewport_info': {
                'current': browser.viewport_current_page + 1,
                'total': len(browser.viewport_pages)
            }
        }
    
    elif action == 'prev_page':
        browser.visit_page(url)
        browser.page_up()
        
        return {
            'url': url,
            'action': action,
            'content': browser.viewport,
            'viewport_info': {
                'current': browser.viewport_current_page + 1,
                'total': len(browser.viewport_pages)
            }
        }
    
    elif action == 'state':
        browser.visit_page(url)
        return browser.get_state()
    
    # Fallback
    return {
        'url': url,
        'action': action,
        'error': f"Unsupported action: {action}"
    }


def custom_text_browser_tool(**kwargs) -> Dict[str, Any]:
    """
    Enhanced text browser tool with safety features and parallel execution.
    
    Examples:
    - Visit page: {"url": "https://example.com", "action": "visit"}
    - Search content: {"url": "https://example.com", "action": "search", "search_query": "news"}
    - Fetch multiple URLs: {"action": "fetch_parallel", "urls": "https://example.com/1,https://example.com/2"}
    
    Security:
    - Automatic proxy rotation
    - Request throttling  
    - User-agent randomization
    """
    try:
        return custom_text_browser_function(**kwargs)
    except Exception as e:
        raise ToolError(f"Browser operation failed: {str(e)}") from e

# Create internal Tool instance
_custom_text_browser_tool = Tool(
    name="custom_text_browser",
    description="""Control a text-based browser to interact with web content. 
Primary actions: 'visit' (load a URL), 'search' (find text on page), 'links' (extract links), 'fetch_parallel' (load multiple URLs). Also supports pagination ('next_page', 'prev_page') and state retrieval ('state').

Features:
- Connection pooling with retry logic
- Randomized headers with user agent rotation  
- Configurable delays between requests
- Parallel URL fetching
- Proxy support with automatic configuration""",
    parameters={
        "url": ParamType.STRING,
        "action": ParamType.STRING,
        "search_query": ParamType.STRING,
        "urls": ParamType.STRING,
        "concurrency": ParamType.INTEGER,
        "use_proxy": ParamType.BOOLEAN,
        "random_delay": ParamType.BOOLEAN,
        "max_retries": ParamType.INTEGER,
        "timeout": ParamType.INTEGER
    },
    func=custom_text_browser_tool,
    rate_limit=10
)

def get_tool() -> Tool:
    """
    Return the custom_text_browser tool instance for tinyAgent integration.

    Returns:
        Tool: The custom_text_browser tool object
    """
    return _custom_text_browser_tool
