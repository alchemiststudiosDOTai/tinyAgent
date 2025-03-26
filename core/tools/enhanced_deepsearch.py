import json
import re
import time
import os
import sys
import subprocess
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from ..decorators import tool
from ..logging import get_logger
from ..agent import get_llm
from ..config import load_config
from .file_manipulator import FileManipulator
from .ripgrep import ripgrep_search
from ..tool import ParamType, Tool
from .custom_text_browser import CustomTextBrowser
from .duckduckgo_search import perform_duckduckgo_search

# Set up logger
logger = get_logger(__name__)


# Import content processor
try:
    from .content_processor import process_content
except ImportError:
    logger.warning("content_processor tool not found, using simplified version")

    def process_content(content, metadata=None, format_type="markdown"):
        """
        Fallback process_content implementation.
        """
        logger.info(f"Using fallback process_content with content type: {type(content)}")

        if metadata is None:
            metadata = {
                "source": "unknown",
                "timestamp": str(time.time()),
                "format": format_type
            }

        return {
            "success": True,
            "processed_content": str(
                content.get("text", str(content))
                if isinstance(content, dict)
                else content
            ),
            "metadata": metadata,
            "quality": {}
        }

class EnhancedDeepSearch:
    """
    Enhanced deep search tool for comprehensive research tasks.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        max_steps: Optional[int] = None,
        debug_level: Optional[int] = None
    ):
        """
        Initialize the enhanced deep search tool.

        Args:
            model: Optional model name to use for LLM
            max_steps: Optional override for max steps per research phase
            debug_level: Optional override for debug level (0-2)
        """
        self.config = load_config()

        agent_config = self.config.get("agent", {})
        tool_config = self.config.get("enhanced_deepsearch", {})

        self.max_steps = max_steps or tool_config.get("max_steps", 2)
        self.debug_level = (
            debug_level
            if debug_level is not None
            else tool_config.get("debug_level", agent_config.get("debug_level", 0))
        )
        self.model = model or tool_config.get(
            "model", agent_config.get("default_model", "deepseek/deepseek-r1")
        )

        # Research phases configuration
        self.research_phases = {
            "gathering": {"max_steps": self.max_steps},
            "analysis": {"max_steps": self.max_steps},
            "synthesis": {"max_steps": self.max_steps},
        }

        print(f"Using model: {self.model}")
        print(f"Max steps per research phase: {self.max_steps}")
        print(f"Debug level: {self.debug_level}")
        print(
            "Configuration source: "
            + (
                "explicit args"
                if max_steps
                else ("tool config" if "max_steps" in tool_config else "defaults")
            )
        )
        print("\nResearch phases:")
        for phase, settings in self.research_phases.items():
            print(f"  - {phase}: {settings['max_steps']} steps")

        self.llm = get_llm(self.model)

        # Initialize components
        self._init_browser()
        self._init_file_manager()
        self._init_tools_registry()

        # Store any relevant context
        self.research_context = {}

        print("\nInitialization complete\n")

    # -------------------------------------------------------------------------
    #                               DRY HELPERS
    # -------------------------------------------------------------------------

    def _debug_print(self, message: str, level: int = 1) -> None:
        """
        Print a debug message if the current debug level meets or exceeds `level`.
        """
        if self.debug_level >= level:
            print(message)

    def _truncate_text(self, text: str, limit: int, label: Optional[str] = None) -> str:
        """
        Truncate text to a given character limit, optionally printing a label for debug.

        Args:
            text: The text to truncate.
            limit: Maximum number of characters allowed.
            label: Optional label for debug printing.

        Returns:
            Truncated text if over the limit, or the original text otherwise.
        """
        if len(text) > limit:
            if label:
                self._debug_print(
                    f"Truncating text from {len(text)} to {limit} characters for {label}",
                    level=1
                )
            else:
                self._debug_print(
                    f"Truncating text from {len(text)} to {limit} characters", level=1
                )
            return text[:limit] + "... [text truncated]"
        return text

    def _llm_call_and_extract_json(
        self,
        prompt: str,
        topic: str = "LLM request"
    ) -> Union[Dict[str, Any], str]:
        """
        Send a prompt to the LLM, then parse out the first JSON block in the response.

        Args:
            prompt: The text prompt to send to the LLM.
            topic: A short label or description for logging/debug.

        Returns:
            A dictionary with the parsed JSON if successful, or a dict with "error" and
            partial response if it fails. In extreme failures, returns a plain string error.
        """
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

            # Attempt to parse JSON
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

    # -------------------------------------------------------------------------
    #                               INITIAL SETUP
    # -------------------------------------------------------------------------

    def _init_browser(self):
        """
        Initialize and configure the text browser with proxy support.
        """
        print("Initializing custom text browser...")
        self.browser = CustomTextBrowser()

        # Configure proxy
        proxy_enabled = self.configure_proxy()
        print(f"Proxy {'enabled' if proxy_enabled else 'disabled'} for browser")

    def _init_file_manager(self):
        """
        Initialize the file manager for local storage.
        """
        print("Initializing file manager...")
        self.file_manager = FileManipulator()

        output_dir = self.config.get("file_operations", {}).get(
            "output_dir", "tinyAgent_output"
        )
        research_dir = os.path.join(output_dir, "research")
        try:
            os.makedirs(research_dir, exist_ok=True)
            print(f"Research output directory: {research_dir}")
        except Exception as exc:
            print(f"Warning: Could not create research directory: {exc}")

    def _init_tools_registry(self):
        """
        Initialize the tools registry with all available tools.
        """
        print("Initializing tools registry...")

        # Register tools for each phase
        self.gathering_tools = {
            "web_search": self._web_search,
            "visit_page": self._visit_page,
            "page_next": self._page_next,
            "page_previous": self._page_previous,
            "find_on_page": self._find_on_page,
            "get_page_links": self._get_page_links,
            "search_local_files": self._search_local_files,
            "read_local_file": self._read_local_file
        }

        self.analysis_tools = {
            "process_text": self._process_text,
            "summarize_text": self._summarize_text,
            "extract_entities": self._extract_entities,
            "analyze_sentiment": self._analyze_sentiment,
            "create_search_plan": self._create_search_plan
        }

        self.synthesis_tools = {
            "generate_summary": self._generate_summary,
            "create_structured_report": self._create_structured_report,
            "save_research_results": self._save_research_results
        }

        print(
            f"Registered {len(self.gathering_tools)} gathering tools, "
            f"{len(self.analysis_tools)} analysis tools, and "
            f"{len(self.synthesis_tools)} synthesis tools"
        )

    def configure_proxy(self) -> bool:
        """
        Configure and test proxy settings from config.
        """
        print("=== CONFIGURING PROXY ===")
        try:
            if not self.config.get("proxy", {}).get("enabled", False):
                print("Proxy disabled in configuration")
                return False

            proxy_config = self.config.get("proxy", {})
            username = proxy_config.get("username")
            password = proxy_config.get("password")
            country = proxy_config.get("country", "US")
            url_template = proxy_config.get("url")

            if not all([username, password, url_template]):
                print("WARNING: Incomplete proxy configuration")
                missing = []
                if not username:
                    missing.append("username")
                if not password:
                    missing.append("password")
                if not url_template:
                    missing.append("url_template")
                print(f"Missing: {', '.join(missing)}")
                return False

            # Format proxy URL with credentials
            try:
                proxy_url = url_template % (username, country, password)
                masked_url = proxy_url.replace(password, "********")
                print(f"Configured proxy URL: {masked_url}")

                if hasattr(self.browser, "use_proxy"):
                    self.browser.use_proxy = True
                    print("Proxy configured for browser")

                return True
            except Exception as exc:
                print(f"ERROR configuring proxy: {str(exc)}")
                return False
        except Exception as exc:
            print(f"ERROR loading proxy configuration: {str(exc)}")
            return False

    # -------------------------------------------------------------------------
    #                           GATHERING PHASE TOOLS
    # -------------------------------------------------------------------------

    def _web_search(
        self,
        keywords: str,
        max_results: int = 5,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        timelimit: Optional[str] = None,
        backend: str = "auto"
    ) -> List[Dict[str, str]]:
        """
        Search the web using DuckDuckGo and return results.
        """
        print("\n=== ENHANCED_DEEPSEARCH WEB_SEARCH DEBUG ===")
        print(
            f"Method called with: keywords={keywords}, max_results={max_results}, "
            f"region={region}, safesearch={safesearch}, timelimit={timelimit}, backend={backend}"
        )

        logger.info(f"Performing web search for: {keywords}")
        try:
            print("Calling perform_duckduckgo_search function...")
            results = perform_duckduckgo_search(
                keywords=keywords,
                max_results=max_results,
                region=region,
                safesearch=safesearch,
                timelimit=timelimit,
                backend=backend
            )

            if results and isinstance(results, list):
                if "error" in results[0]:
                    print(f"Search error: {results[0].get('error')}")
                else:
                    print(f"\nFound {len(results)} search results for '{keywords}':")
                    print("=" * 100)

                    for i, result in enumerate(results, 1):
                        print(f"\nResult {i}:")
                        print("-" * 50)

                        title = result.get('title', 'No title')
                        print(f"Title: {title}")

                        url = result.get('url', 'No URL')
                        print(f"URL: {url}")

                        snippet = result.get('snippet', 'No snippet')
                        print("\nSnippet:")
                        print("-" * 30)
                        print(snippet)
                        print("-" * 30)

                        if self.debug_level > 1:
                            print("\nAdditional Data:")
                            print("-" * 30)
                            print(json.dumps(result, indent=2))
                            print("-" * 30)

                        print("\n")

                    print("=" * 100)
                    print(f"End of {len(results)} results for '{keywords}'\n")
            else:
                print("No results or unexpected format")

            return results
        except Exception as exc:
            logger.error(f"Error during web search: {str(exc)}")
            print(f"Exception in _web_search: {str(exc)}")
            return [{"error": f"Search error: {str(exc)}"}]
        finally:
            print("=== END ENHANCED_DEEPSEARCH WEB_SEARCH DEBUG ===\n")

    def _visit_page(self, url: str) -> str:
        """
        Visit a web page and return its content.

        Args:
            url: URL to visit

        Returns:
            Text content of the page
        """
        print(f"\n=== VISITING PAGE: {url} ===")
        logger.info(f"Visiting page: {url}")
        try:
            content = self.browser.visit_page(url)
            print(f"Retrieved {len(content)} characters of content")
            if self.debug_level > 1:
                preview = (
                    content[:200].replace('\n', ' ') + "..."
                    if len(content) > 200
                    else content
                )
                print(f"Content preview: {preview}")
            return content
        except Exception as exc:
            error_msg = f"Error visiting page: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return error_msg
        finally:
            print("=== END VISITING PAGE ===\n")

    def _page_next(self) -> str:
        """
        Move to the next page/viewport of content and return it.
        """
        print("\n=== NAVIGATING TO NEXT PAGE ===")
        logger.info("Moving to next page")
        try:
            self.browser.page_down()
            content = self.browser.viewport
            viewport_info = (
                f"Viewport {self.browser.viewport_current_page + 1}/"
                f"{len(self.browser.viewport_pages)}"
            )
            print(f"Moved to {viewport_info}")
            return content
        except Exception as exc:
            error_msg = f"Error moving to next page: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return error_msg
        finally:
            print("=== END NAVIGATING TO NEXT PAGE ===\n")

    def _page_previous(self) -> str:
        """
        Move to the previous page/viewport of content and return it.
        """
        print("\n=== NAVIGATING TO PREVIOUS PAGE ===")
        logger.info("Moving to previous page")
        try:
            self.browser.page_up()
            content = self.browser.viewport
            viewport_info = (
                f"Viewport {self.browser.viewport_current_page + 1}/"
                f"{len(self.browser.viewport_pages)}"
            )
            print(f"Moved to {viewport_info}")
            return content
        except Exception as exc:
            error_msg = f"Error moving to previous page: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return error_msg
        finally:
            print("=== END NAVIGATING TO PREVIOUS PAGE ===\n")

    def _find_on_page(self, query: str) -> str:
        """
        Search for text on the current page.

        Args:
            query: Text to search for

        Returns:
            Viewport content containing the search result or a message if not found
        """
        print(f"\n=== SEARCHING PAGE FOR: {query} ===")
        logger.info(f"Searching for '{query}' on page")
        try:
            result = self.browser.find_on_page(query)
            if result:
                print(f"Found match in viewport {self.browser.viewport_current_page + 1}")
                if self.debug_level > 1:
                    preview = (
                        result[:200].replace('\n', ' ') + "..."
                        if len(result) > 200
                        else result
                    )
                    print(f"Result preview: {preview}")
                return result
            else:
                print("Search term not found on page")
                return "Search term not found on page."
        except Exception as exc:
            error_msg = f"Error searching page: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return error_msg
        finally:
            print("=== END SEARCHING PAGE ===\n")

    def _get_page_links(self) -> List[Dict[str, str]]:
        """
        Get links from the current page.

        Returns:
            List of dictionaries containing link text and URLs
        """
        print("\n=== EXTRACTING PAGE LINKS ===")
        logger.info("Getting links from page")
        try:
            links = self.browser.get_links()
            print(f"Found {len(links)} links on the current page")
            if self.debug_level > 1 and links:
                print("First 3 links:")
                for i, link in enumerate(links[:3]):
                    text_val = link.get('text', 'No text')
                    url_val = link.get('url', 'No URL')
                    print(f"  {i+1}: {text_val} -> {url_val}")
            return links
        except Exception as exc:
            error_msg = f"Error getting page links: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return [{"error": error_msg}]
        finally:
            print("=== END EXTRACTING PAGE LINKS ===\n")

    def _search_local_files(
        self,
        query: str,
        path: str = "./",
        file_pattern: str = "*"
    ) -> List[Dict[str, Any]]:
        """
        Search for text in local files.

        Args:
            query: Text to search for
            path: Path to search in
            file_pattern: Pattern of files to search

        Returns:
            List of dictionaries with file and match information
        """
        print("\n=== SEARCHING LOCAL FILES ===")
        print(f"Query: {query}, Path: {path}, Pattern: {file_pattern}")
        try:
            results = ripgrep_search(query, path, f"--glob '{file_pattern}'", json_output=True)
            try:
                parsed_results = json.loads(results)
                print(f"Found matches in {len(parsed_results)} files")
                return parsed_results
            except Exception:
                return [{
                    "error": f"Failed to parse search results: {results[:100]}..."
                }]
        except Exception as exc:
            error_msg = f"Error searching files: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return [{"error": error_msg}]
        finally:
            print("=== END SEARCHING LOCAL FILES ===\n")

    def _read_local_file(self, path: str) -> Dict[str, Any]:
        """
        Read content from a local file.

        Args:
            path: Path to the file

        Returns:
            Dictionary with file content and metadata
        """
        print(f"\n=== READING LOCAL FILE: {path} ===")
        try:
            result = self.file_manager.read_file(path)
            if result.get("status") == "success":
                content = result.get("content", "")
                print(f"Read {len(content)} characters from file")
                if self.debug_level > 1:
                    preview = (
                        content[:200].replace('\n', ' ') + "..."
                        if len(content) > 200
                        else content
                    )
                    print(f"Content preview: {preview}")
                return {
                    "success": True,
                    "content": content,
                    "path": path
                }
            else:
                error_msg = f"Failed to read file: {result.get('error', 'Unknown error')}"
                print(error_msg)
                return {"success": False, "error": error_msg}
        except Exception as exc:
            error_msg = f"Error reading file: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return {"success": False, "error": error_msg}
        finally:
            print("=== END READING LOCAL FILE ===\n")

    # -------------------------------------------------------------------------
    #                         ANALYSIS & SYNTHESIS TOOLS
    # -------------------------------------------------------------------------

    def _process_text(self, text: str) -> str:
        """
        Process text content using the content_processor tool.
        """
        print(f"\n=== PROCESSING TEXT ===")
        print(f"Text length: {len(text)} characters")
        logger.info(f"Processing text (length: {len(text)})")

        try:
            text = self._truncate_text(text, 10000, label="processing")

            content = {"text": text}
            metadata = {
                "source": "text_processing",
                "timestamp": str(time.time())
            }

            # Call process_content
            try:
                result = process_content(
                    content=content, metadata=metadata, format_type="markdown"
                )
            except TypeError as exc:
                # If keyword arguments fail, try positional arguments
                print(f"Keyword arguments failed: {exc}, trying positional arguments")
                try:
                    result = process_content(content, metadata, "markdown")
                except Exception as exc2:
                    print(f"Positional arguments also failed: {exc2}")
                    return text

            if result and result.get("success", False):
                processed = result.get("processed_content", text)
                print(
                    f"Successfully processed text, "
                    f"result length: {len(processed)} characters"
                )
                return processed
            else:
                error_msg = (
                    f"Processing error: {result.get('error', 'Unknown error')}"
                    if result else "No result returned"
                )
                print(error_msg)
                return text

        except Exception as exc:
            error_msg = f"Error processing text: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return text
        finally:
            print("=== END PROCESSING TEXT ===\n")

    def _summarize_text(self, text: str) -> str:
        """
        Summarize the provided text using the internal LLM.
        """
        print(f"\n=== SUMMARIZING TEXT ===")
        print(f"Text length: {len(text)} characters")
        logger.info("Summarizing text with internal LLM")

        try:
            text = self._truncate_text(text, 8000, label="summarizing")

            prompt = (
                f"Please summarize the following text concisely, focusing on "
                f"the key points:\n\n{text}\n\nSummary:"
            )

            print("Sending to LLM for summarization...")
            summary = self.llm(prompt)
            print(f"Successfully generated summary, length: {len(summary)} characters")
            if self.debug_level > 1:
                preview = (
                    summary[:200].replace('\n', ' ') + "..."
                    if len(summary) > 200
                    else summary
                )
                print(f"Summary preview: {preview}")
            return summary
        except Exception as exc:
            error_msg = f"Error summarizing text: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return error_msg
        finally:
            print("=== END SUMMARIZING TEXT ===\n")

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract entities (people, organizations, locations, dates) from text.
        """
        print(f"\n=== EXTRACTING ENTITIES ===")
        print(f"Text length: {len(text)} characters")

        # We'll truncate for safety
        text = self._truncate_text(text, 5000, label="entity extraction")

        prompt = (
            "Extract the following entity types from the text below:\n"
            "1. People (real individuals)\n"
            "2. Organizations (companies, institutions, groups)\n"
            "3. Locations (countries, cities, places)\n"
            "4. Dates (specific dates, periods, timeframes)\n"
            "5. Key concepts (important ideas, terms, technologies)\n\n"
            "Return the results in the following JSON format:\n"
            "{\n"
            '"people": ["person1", "person2", ...],\n'
            '"organizations": ["org1", "org2", ...],\n'
            '"locations": ["location1", "location2", ...],\n'
            '"dates": ["date1", "date2", ...],\n'
            '"key_concepts": ["concept1", "concept2", ...]\n'
            "}\n\n"
            f"TEXT:\n{text}"
        )

        try:
            result = self._llm_call_and_extract_json(prompt, topic="entity extraction")
            if isinstance(result, dict) and "error" not in result:
                entities = result
                print("Successfully extracted entities:")
                for category, items in entities.items():
                    print(f"  - {category}: {len(items)} items")
                    if self.debug_level > 1 and items:
                        print(f"    First 3: {', '.join(items[:3])}")
                return entities
            else:
                # Return error structure
                if isinstance(result, dict):
                    return result  # has "error" and possibly "raw_response"
                return {"error": str(result)}
        finally:
            print("=== END EXTRACTING ENTITIES ===\n")

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment and tone of text.
        """
        print(f"\n=== ANALYZING SENTIMENT ===")
        print(f"Text length: {len(text)} characters")

        text = self._truncate_text(text, 3000, label="sentiment analysis")

        prompt = (
            "Analyze the sentiment, tone, and subjectivity of the following text.\n\n"
            "Return the results in the following JSON format:\n"
            "{\n"
            '"sentiment": "positive" or "negative" or "neutral",\n'
            '"sentiment_score": a number between -1.0 and 1.0,\n'
            '"tone": ["analytical", "confident", "tentative", etc.],\n'
            '"subjectivity": "objective"/"somewhat objective"/"somewhat subjective"/"subjective",\n'
            '"key_emotional_phrases": ["phrase1", "phrase2", ...]\n'
            "}\n\n"
            f"TEXT:\n{text}"
        )

        try:
            result = self._llm_call_and_extract_json(prompt, topic="sentiment analysis")
            if isinstance(result, dict) and "error" not in result:
                sentiment = result
                print("Successfully analyzed sentiment:")
                print(f"  - Overall sentiment: {sentiment.get('sentiment', 'unknown')}")
                print(f"  - Score: {sentiment.get('sentiment_score', 'unknown')}")
                tone_list = sentiment.get('tone', [])
                print(f"  - Tone: {', '.join(tone_list)}")
                return sentiment
            else:
                if isinstance(result, dict):
                    return result  # has "error" and possibly "raw_response"
                return {"error": str(result)}
        finally:
            print("=== END ANALYZING SENTIMENT ===\n")

    def _create_search_plan(
        self, query: str, initial_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a search plan based on initial results.
        """
        print(f"\n=== CREATING SEARCH PLAN ===")
        print(f"Query: {query}")
        print(f"Number of initial results: {len(initial_results)}")

        formatted_results = []
        for i, result in enumerate(initial_results[:5]):
            formatted_results.append(
                f"Result {i+1}:\n"
                f"Title: {result.get('title', 'No title')}\n"
                f"URL: {result.get('url', 'No URL')}\n"
                f"Snippet: {result.get('snippet', 'No snippet')}\n"
            )
        results_text = "\n".join(formatted_results)

        plan_prompt = (
            "Based on the original query and initial search results, "
            "create a detailed search plan.\n"
            "Identify knowledge gaps and additional searches needed.\n\n"
            f"Original query: {query}\n\n"
            f"Initial search results:\n{results_text}\n"
            "Return the search plan in JSON format:\n"
            "{\n"
            '"identified_topics": ["topic1", "topic2", ...],\n'
            '"knowledge_gaps": ["gap1", "gap2", ...],\n'
            '"additional_searches": [\n'
            '   {\n'
            '       "search_query": "specific query text",\n'
            '       "purpose": "aim of this search",\n'
            '       "priority": "high"/"medium"/"low"\n'
            '   },\n'
            '   ...\n'
            '],\n'
            '"recommended_sources": ["source1", "source2", ...],\n'
            '"expected_challenges": ["challenge1", "challenge2", ...]\n'
            "}"
        )

        try:
            result = self._llm_call_and_extract_json(plan_prompt, topic="search plan")
            if isinstance(result, dict) and "error" not in result:
                plan = result
                print("Successfully created search plan:")
                print(
                    f"  - Identified topics: {len(plan.get('identified_topics', []))} topics"
                )
                print(
                    f"  - Knowledge gaps: {len(plan.get('knowledge_gaps', []))} gaps"
                )
                as_list = plan.get("additional_searches", [])
                print(f"  - Additional searches: {len(as_list)} total")
                if self.debug_level > 1 and as_list:
                    for i, search_item in enumerate(as_list[:3]):
                        sq = search_item.get('search_query')
                        prio = search_item.get('priority')
                        print(f"    Search {i+1}: {sq} (Priority: {prio})")
                return plan
            else:
                if isinstance(result, dict):
                    return result
                return {"error": str(result)}
        finally:
            print("=== END CREATING SEARCH PLAN ===\n")

    def _generate_summary(
        self,
        query: str,
        findings: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a concise summary of research findings.
        """
        print(f"\n=== GENERATING SUMMARY ===")
        print(f"Query: {query}")
        print(f"Number of findings: {len(findings)}")

        formatted_findings = []
        for i, finding in enumerate(findings):
            if isinstance(finding, dict):
                if 'text' in finding:
                    snippet = finding['text'][:500]
                elif 'content' in finding:
                    snippet = finding['content'][:500]
                else:
                    snippet = json.dumps(finding)[:500]
                formatted_findings.append(f"Finding {i+1}: {snippet}...")
            elif isinstance(finding, str):
                formatted_findings.append(f"Finding {i+1}: {finding[:500]}...")
            else:
                formatted_findings.append(f"Finding {i+1}: {str(finding)[:500]}...")

        findings_text = "\n\n".join(formatted_findings)

        prompt = (
            "Generate a concise, informative summary of the following research findings.\n"
            "The summary should directly answer the original query and synthesize the key points.\n\n"
            f"Original query: {query}\n\n"
            f"Research findings:\n{findings_text}\n\n"
            "Your summary should:\n"
            "1. Directly answer the query\n"
            "2. Highlight the most important facts\n"
            "3. Present a balanced view if there's conflicting info\n"
            "4. Be well-structured\n"
            "5. Cite findings where appropriate\n"
        )

        try:
            print("Sending to LLM to generate summary...")
            summary = self.llm(prompt)
            print(f"Successfully generated summary, length: {len(summary)} characters")
            if self.debug_level > 1:
                preview = (
                    summary[:200].replace('\n', ' ') + "..."
                    if len(summary) > 200
                    else summary
                )
                print(f"Summary preview: {preview}")
            return summary
        except Exception as exc:
            error_msg = f"Error generating summary: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return error_msg
        finally:
            print("=== END GENERATING SUMMARY ===\n")

    def _create_structured_report(
        self,
        query: str,
        findings: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a structured report from research findings.
        """
        print(f"\n=== CREATING STRUCTURED REPORT ===")
        print(f"Query: {query}")
        print(f"Number of findings: {len(findings)}")

        formatted_findings = []
        for i, finding in enumerate(findings):
            if isinstance(finding, dict):
                if 'text' in finding:
                    snippet = finding['text'][:500]
                elif 'content' in finding:
                    snippet = finding['content'][:500]
                else:
                    snippet = json.dumps(finding)[:500]
                formatted_findings.append(f"Finding {i+1}: {snippet}...")
            elif isinstance(finding, str):
                formatted_findings.append(f"Finding {i+1}: {finding[:500]}...")
            else:
                formatted_findings.append(f"Finding {i+1}: {str(finding)[:500]}...")

        findings_text = "\n\n".join(formatted_findings)

        metadata_text = ""
        if metadata:
            metadata_text = "\nMetadata:\n" + json.dumps(metadata, indent=2)

        # Improved formal report structure template
        prompt = (
            "Create a comprehensive, academic-style research report based on the findings provided.\n"
            "The report should follow a formal structure with clear, well-organized sections and subsections.\n\n"
            f"Original query: {query}\n\n"
            f"Research findings:\n{findings_text}{metadata_text}\n\n"
            "Return the report in the following JSON format:\n"
            "{\n"
            '"report_title": "A descriptive title for the research report",\n'
            '"abstract": "A concise summary of the research question, methodology, findings, and significance",\n'
            '"keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],\n'
            '"table_of_contents": ["1. Introduction", "2. Background", "3. Methodology", "4. Results", "5. Discussion", "6. Conclusion", "7. References"],\n'
            '"sections": [\n'
            '   {\n'
            '       "title": "1. Introduction",\n'
            '       "content": "Introduction text with clear problem statement and objectives",\n'
            '       "subsections": [\n'
            '           {"title": "1.1 Research Question", "content": "Clearly stated research question"},\n'
            '           {"title": "1.2 Significance", "content": "Why this research matters"}\n'
            '       ]\n'
            '   },\n'
            '   {\n'
            '       "title": "2. Background",\n'
            '       "content": "Context and literature review",\n'
            '       "subsections": [\n'
            '           {"title": "2.1 Historical Context", "content": "Evolution of the field"},\n'
            '           {"title": "2.2 Current State of Knowledge", "content": "What is already known"}\n'
            '       ]\n'
            '   },\n'
            '   {\n'
            '       "title": "3. Methodology",\n'
            '       "content": "Approach and methods used",\n'
            '       "subsections": [\n'
            '           {"title": "3.1 Data Collection", "content": "How information was gathered"},\n'
            '           {"title": "3.2 Analysis Framework", "content": "How information was analyzed"}\n'
            '       ]\n'
            '   },\n'
            '   {\n'
            '       "title": "4. Results",\n'
            '       "content": "Main findings presented objectively",\n'
            '       "subsections": [\n'
            '           {"title": "4.1 Primary Findings", "content": "Key discoveries"},\n'
            '           {"title": "4.2 Secondary Findings", "content": "Additional insights"}\n'
            '       ]\n'
            '   },\n'
            '   {\n'
            '       "title": "5. Discussion",\n'
            '       "content": "Interpretation of results",\n'
            '       "subsections": [\n'
            '           {"title": "5.1 Implications", "content": "What the results mean"},\n'
            '           {"title": "5.2 Limitations", "content": "Constraints and weaknesses"}\n'
            '       ]\n'
            '   },\n'
            '   {\n'
            '       "title": "6. Conclusion",\n'
            '       "content": "Summary of key findings and their significance",\n'
            '       "subsections": [\n'
            '           {"title": "6.1 Summary", "content": "Recap of main points"},\n'
            '           {"title": "6.2 Future Directions", "content": "Potential next steps for research"}\n'
            '       ]\n'
            '   }\n'
            '],\n'
            '"references": [\n'
            '   {\n'
            '       "citation": "Author, A. (Year). Title. Journal/Source, Volume(Issue), Pages",\n'
            '       "url": "URL if available",\n'
            '       "relevance": "High/Medium/Low",\n'
            '       "key_contribution": "Brief note on how this source contributes to the research"\n'
            '   }\n'
            '],\n'
            '"appendices": [\n'
            '   {\n'
            '       "title": "Appendix A: Additional Data",\n'
            '       "content": "Supplementary materials"\n'
            '   }\n'
            '],\n'
            '"metadata": {\n'
            '   "generation_timestamp": "Current date and time",\n'
            '   "query": "Original research query",\n'
            '   "data_sources": ["List of sources used"],\n'
            '   "methodology_notes": "Brief description of research approach"\n'
            '}\n'
            "}"
        )

        try:
            result = self._llm_call_and_extract_json(prompt, topic="structured report creation")
            if isinstance(result, dict) and "error" not in result:
                report = result
                print("Successfully created structured report")
                print(f"  - Report title: {report.get('report_title', 'No title')}")
                print(f"  - Sections: {len(report.get('sections', []))} total")
                if self.debug_level > 1:
                    preview = json.dumps(report, indent=2)[:500] + "..."
                    print("Report preview:")
                    print(preview)
                return report
            else:
                if isinstance(result, dict):
                    return result
                return {"error": str(result)}
        finally:
            print("=== END CREATING STRUCTURED REPORT ===\n")

    def _save_research_results(
        self,
        query: str,
        findings: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        output_format: str = "both"
    ) -> Dict[str, Any]:
        """
        Save research findings to files in structured formats.

        Args:
            query: Original research query
            findings: List of research findings
            metadata: Optional metadata about the research
            output_format: Format to save results in ("json", "markdown", or "both")

        Returns:
            Dictionary containing save operation results
        """
        print(f"\n=== SAVING RESEARCH RESULTS ===")
        print(f"Query: {query}")
        print(f"Number of findings: {len(findings)}")
        print(f"Output format: {output_format}")

        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            research_dir = os.path.join(
                self.config.get("file_operations", {}).get(
                    "output_dir", "tinyAgent_output"
                ),
                "research"
            )
            query_dir = os.path.join(research_dir, f"query_{timestamp}")
            os.makedirs(query_dir, exist_ok=True)
            print(f"Created research directory: {query_dir}")

            if metadata is None:
                metadata = {}
            metadata.update({
                "timestamp": timestamp,
                "query": query,
                "findings_count": len(findings)
            })

            results = {
                "success": True,
                "saved_files": [],
                "metadata": metadata
            }

            # Save JSON format if requested
            if output_format in ["json", "both"]:
                json_path = os.path.join(query_dir, "research_results.json")
                try:
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(
                            {
                                "query": query,
                                "findings": findings,
                                "metadata": metadata
                            },
                            f,
                            indent=2,
                            ensure_ascii=False
                        )
                    results["saved_files"].append(json_path)
                    print(f"Saved JSON results to: {json_path}")
                except Exception as exc:
                    error_msg = f"Error saving JSON results: {str(exc)}"
                    logger.error(error_msg)
                    print(error_msg)
                    results["json_error"] = error_msg

            # Save Markdown format if requested
            if output_format in ["markdown", "both"]:
                md_path = os.path.join(query_dir, "research_results.md")
                try:
                    with open(md_path, 'w', encoding='utf-8') as f:
                        # Find a proper report to format nicely
                        structured_report = None
                        for finding in findings:
                            if (isinstance(finding, dict) and 
                                finding.get("type") == "structured_report" and 
                                isinstance(finding.get("content"), dict)):
                                structured_report = finding.get("content")
                                break
                        
                        if structured_report and "report_title" in structured_report:
                            # Format using new formal report template
                            f.write(f"# {structured_report.get('report_title', 'Research Results')}\n\n")
                            
                            # Abstract
                            if "abstract" in structured_report:
                                f.write(f"## Abstract\n\n{structured_report['abstract']}\n\n")
                            
                            # Keywords
                            if "keywords" in structured_report and structured_report["keywords"]:
                                f.write(f"**Keywords**: {', '.join(structured_report['keywords'])}\n\n")
                            
                            # Table of Contents
                            if "table_of_contents" in structured_report and structured_report["table_of_contents"]:
                                f.write("## Table of Contents\n\n")
                                for item in structured_report["table_of_contents"]:
                                    f.write(f"- {item}\n")
                                f.write("\n")
                            
                            # Sections
                            if "sections" in structured_report:
                                for section in structured_report["sections"]:
                                    f.write(f"## {section.get('title', 'Section')}\n\n")
                                    f.write(f"{section.get('content', '')}\n\n")
                                    
                                    if "subsections" in section:
                                        for subsection in section["subsections"]:
                                            f.write(f"### {subsection.get('title', 'Subsection')}\n\n")
                                            f.write(f"{subsection.get('content', '')}\n\n")
                            
                            # References
                            if "references" in structured_report and structured_report["references"]:
                                f.write("## References\n\n")
                                for i, ref in enumerate(structured_report["references"], 1):
                                    f.write(f"{i}. {ref.get('citation', 'No citation')}")
                                    if ref.get('url'):
                                        f.write(f" [{ref['url']}]({ref['url']})")
                                    f.write("\n")
                                f.write("\n")
                            
                            # Appendices
                            if "appendices" in structured_report and structured_report["appendices"]:
                                for appendix in structured_report["appendices"]:
                                    f.write(f"## {appendix.get('title', 'Appendix')}\n\n")
                                    f.write(f"{appendix.get('content', '')}\n\n")
                            
                            # Metadata
                            if "metadata" in structured_report:
                                f.write("## Research Metadata\n\n```json\n")
                                f.write(json.dumps(structured_report["metadata"], indent=2))
                                f.write("\n```\n")
                        else:
                            # Fall back to old format if no structured report
                            f.write(f"# Research Results: {query}\n\n")
                            f.write(f"Generated on: {timestamp}\n\n")

                            f.write("## Metadata\n\n")
                            f.write("```json\n")
                            f.write(json.dumps(metadata, indent=2))
                            f.write("\n```\n\n")

                            f.write("## Findings\n\n")
                            for i, finding in enumerate(findings, 1):
                                f.write(f"### Finding {i}\n\n")
                                if isinstance(finding, dict):
                                    if finding.get("type") == "summary" and "content" in finding:
                                        f.write(finding["content"])
                                    elif 'text' in finding:
                                        if isinstance(finding['text'], str):
                                            f.write(finding['text'])
                                        else:
                                            f.write(json.dumps(finding['text'], indent=2))
                                    elif 'content' in finding:
                                        if isinstance(finding['content'], str):
                                            f.write(finding['content'])
                                        else:
                                            f.write(json.dumps(finding['content'], indent=2))
                                    else:
                                        f.write(json.dumps(finding, indent=2))
                                elif isinstance(finding, str):
                                    f.write(finding)
                                else:
                                    f.write(str(finding))
                                f.write("\n\n")

                    results["saved_files"].append(md_path)
                    print(f"Saved Markdown results to: {md_path}")
                except Exception as exc:
                    error_msg = f"Error saving Markdown results: {str(exc)}"
                    logger.error(error_msg)
                    print(error_msg)
                    results["markdown_error"] = error_msg

            # Save raw findings if any errors occurred
            if "json_error" in results or "markdown_error" in results:
                raw_path = os.path.join(query_dir, "raw_findings.json")
                try:
                    with open(raw_path, 'w', encoding='utf-8') as f:
                        json.dump(findings, f, indent=2, ensure_ascii=False)
                    results["saved_files"].append(raw_path)
                    print(f"Saved raw findings to: {raw_path}")
                except Exception as exc:
                    error_msg = f"Error saving raw findings: {str(exc)}"
                    logger.error(error_msg)
                    print(error_msg)
                    results["raw_error"] = error_msg

            print("\nSave operation complete:")
            print(f"  - Total files saved: {len(results['saved_files'])}")
            if "json_error" in results:
                print(f"  - JSON save error: {results['json_error']}")
            if "markdown_error" in results:
                print(f"  - Markdown save error: {results['markdown_error']}")
            if "raw_error" in results:
                print(f"  - Raw save error: {results['raw_error']}")

            return results

        except Exception as exc:
            error_msg = f"Error saving research results: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        finally:
            print("=== END SAVING RESEARCH RESULTS ===\n")

    # -------------------------------------------------------------------------
    #                  END-TO-END RESEARCH FLOW METHODS
    # -------------------------------------------------------------------------

    def process_query(
        self,
        query: str,
        max_steps: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process a research query through all phases of research.

        Args:
            query: The research query to process
            max_steps: Optional override for max steps per phase

        Returns:
            Dictionary containing research results and metadata
        """
        print(f"\n=== PROCESSING RESEARCH QUERY ===")
        print(f"Query: {query}")
        print(f"Max steps per research phase: {max_steps or self.max_steps}")

        research_state = {}
        try:
            research_state = {
                "query": query,
                "start_time": time.time(),
                "phases": {
                    "gathering": {"status": "pending", "findings": [], "steps": 0},
                    "analysis": {"status": "pending", "findings": [], "steps": 0},
                    "synthesis": {"status": "pending", "findings": [], "steps": 0}
                },
                "metadata": {
                    "model": self.model,
                    "max_steps": max_steps or self.max_steps,
                    "debug_level": self.debug_level
                }
            }

            # Phase 1: Information Gathering
            print("\n=== PHASE 1: INFORMATION GATHERING ===")
            gathering_results = self._gather_information(query, max_steps)
            research_state["phases"]["gathering"].update({
                "status": "completed",
                "findings": gathering_results.get("findings", []),
                "steps": gathering_results.get("steps", 0)
            })

            # Phase 2: Analysis & Planning
            print("\n=== PHASE 2: ANALYSIS & PLANNING ===")
            analysis_results = self._analyze_findings(
                query,
                gathering_results.get("findings", []),
                max_steps
            )
            research_state["phases"]["analysis"].update({
                "status": "completed",
                "findings": analysis_results.get("findings", []),
                "steps": analysis_results.get("steps", 0)
            })

            # Phase 3: Synthesis & Reporting
            print("\n=== PHASE 3: SYNTHESIS & REPORTING ===")
            synthesis_results = self._synthesize_results(
                query,
                gathering_results.get("findings", []),
                analysis_results.get("findings", []),
                max_steps
            )
            research_state["phases"]["synthesis"].update({
                "status": "completed",
                "findings": synthesis_results.get("findings", []),
                "steps": synthesis_results.get("steps", 0)
            })

            research_state["metadata"].update({
                "end_time": time.time(),
                "total_duration": time.time() - research_state["start_time"],
                "total_steps": sum(
                    phase["steps"] for phase in research_state["phases"].values()
                )
            })

            # Save results
            save_results = self._save_research_results(
                query,
                synthesis_results.get("findings", []),
                research_state["metadata"]
            )
            research_state["save_results"] = save_results

            print("\n=== RESEARCH COMPLETED ===")
            print(
                f"Total duration: {research_state['metadata']['total_duration']:.2f} seconds"
            )
            print(f"Total steps: {research_state['metadata']['total_steps']}")
            print("\nPhase summaries:")
            for phase, data in research_state["phases"].items():
                print(
                    f"  - {phase.title()}: {data['steps']} steps, "
                    f"{len(data['findings'])} findings"
                )

            return research_state

        except Exception as exc:
            error_msg = f"Error processing research query: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "research_state": research_state if research_state else None
            }
        finally:
            print("=== END PROCESSING RESEARCH QUERY ===\n")

    # -------------------------------------------------------------------------
    #                     INTERNAL HELPERS FOR WORKFLOW
    # -------------------------------------------------------------------------

    def _gather_information(
        self,
        query: str,
        max_steps: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Gather information from various sources.
        """
        steps = 0
        findings = []
        max_steps = max_steps or self.max_steps

        try:
            # Initial web search
            search_results = self._web_search(query)
            findings.extend(search_results)
            steps += 1

            # Create search plan
            search_plan = self._create_search_plan(query, search_results)
            if (
                isinstance(search_plan, dict)
                and "additional_searches" in search_plan
            ):
                for search in search_plan["additional_searches"]:
                    if steps >= max_steps:
                        break
                    sq = search.get("search_query")
                    if sq:
                        additional_results = self._web_search(sq)
                        findings.extend(additional_results)
                        steps += 1

            return {
                "success": True,
                "findings": findings,
                "steps": steps
            }
        except Exception as exc:
            error_msg = f"Error gathering information: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "findings": findings,
                "steps": steps
            }

    def _analyze_findings(
        self,
        query: str,
        findings: List[Dict[str, Any]],
        max_steps: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze gathered findings.
        """
        steps = 0
        analyzed_findings = []
        max_steps = max_steps or self.max_steps

        try:
            for finding in findings:
                if steps >= max_steps:
                    break

                # Extract text content
                if isinstance(finding, dict):
                    if 'text' in finding:
                        text = finding['text']
                    elif 'content' in finding:
                        text = finding['content']
                    else:
                        text = json.dumps(finding)
                elif isinstance(finding, str):
                    text = finding
                else:
                    text = str(finding)

                processed = self._process_text(text)
                if processed:
                    entities = self._extract_entities(processed)
                    analyzed_findings.append({
                        "original": finding,
                        "processed": processed,
                        "entities": entities
                    })
                    steps += 1

            return {
                "success": True,
                "findings": analyzed_findings,
                "steps": steps
            }
        except Exception as exc:
            error_msg = f"Error analyzing findings: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "findings": analyzed_findings,
                "steps": steps
            }

    def _synthesize_results(
        self,
        query: str,
        gathering_findings: List[Dict[str, Any]],
        analysis_findings: List[Dict[str, Any]],
        max_steps: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Synthesize research results.
        """
        steps = 0
        synthesized_findings = []
        max_steps = max_steps or self.max_steps

        try:
            # Generate summary
            if steps < max_steps:
                summary = self._generate_summary(query, gathering_findings)
                if summary:
                    synthesized_findings.append({
                        "type": "summary",
                        "content": summary
                    })
                    steps += 1

            # Create structured report
            if steps < max_steps:
                report = self._create_structured_report(query, gathering_findings)
                if isinstance(report, dict):
                    synthesized_findings.append({
                        "type": "structured_report",
                        "content": report
                    })
                    steps += 1

            return {
                "success": True,
                "findings": synthesized_findings,
                "steps": steps
            }
        except Exception as exc:
            error_msg = f"Error synthesizing results: {str(exc)}"
            logger.error(error_msg)
            print(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "findings": synthesized_findings,
                "steps": steps
            }

# Create the tool instance for direct usage
enhanced_deepsearch_tool = EnhancedDeepSearch()

@tool(
    name="enhanced_deepsearch",
    description="A comprehensive research tool that can gather, analyze, and synthesize information from various sources"
)
def enhanced_deepsearch_tool_wrapper(query: str, max_steps: Optional[int] = None) -> Dict[str, Any]:
    """
    Enhanced deep search tool for comprehensive research tasks.
    
    Args:
        query: The research query or topic to investigate
        max_steps: Optional maximum number of steps per research phase
        
    Returns:
        Dictionary containing research results and metadata
    """
    searcher = EnhancedDeepSearch(max_steps=max_steps)
    return searcher.process_query(query, max_steps)

# Create a proper Tool instance for the wrapper
from ..tool import Tool, ParamType
enhanced_deepsearch_tool_wrapper._tool = Tool(
    name="enhanced_deepsearch",
    description="A comprehensive research tool that can gather, analyze, and synthesize information from various sources",
    parameters={
        "query": ParamType.STRING,
        "max_steps": ParamType.INTEGER
    },
    func=enhanced_deepsearch_tool_wrapper
)

# Export both the class instance and the tool wrapper
__all__ = ['enhanced_deepsearch_tool', 'enhanced_deepsearch_tool_wrapper', 'EnhancedDeepSearch']
