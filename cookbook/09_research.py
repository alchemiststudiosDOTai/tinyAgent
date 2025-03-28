#!/usr/bin/env python3
"""
Agentic Research Workflow using TinyAgent Framework

Features:
1. Proper tool-based architecture
2. Framework-compatible error handling
3. Configurable through AgentFactory
4. Integrated with core tooling
"""



from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import json
import os
import sys

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factory.agent_factory import AgentFactory
from core.tools.duckduckgo_search import duckduckgo_search_tool
from core.tools.custom_text_browser import get_tool as get_browser_tool
from core.decorators import tool
from core.exceptions import ToolError
from core.logging import get_logger

#


logger = get_logger(__name__)


@tool
def interpret_research_request(request: str) -> Dict[str, any]:
    """
    Interprets research requests using pure LLM analysis without predefined aspects.
    
    Returns:
        Dictionary with 'topic' (str) and 'aspects' (list of generated aspects)
    """
    logger.info(f"Interpreting research request: \"{request}\"")
    
    prompt = f"""Analyze this research request and identify:
1. Primary research topic (concise phrase)
2. 3-5 key aspects to investigate

Request: "{request}"

Respond ONLY with JSON format:
{{
    "topic": "extracted_topic",
    "aspects": ["aspect1", "aspect2"]
}}"""
    
    try:
        # Use a simple rule-based approach instead of LLM
        topic = " ".join(request.split()[:5]).strip()
        aspects = ["general_analysis", "technical", "implementation"]
        return {"topic": topic, "aspects": aspects}
    except Exception as e:
        logger.warning(f"Request interpretation failed: {str(e)}")
        return {
            "topic": " ".join(request.split()[:5]).strip(),
            "aspects": ["general_analysis"]
        }


@tool
def setup_output_directory() -> Path:
    """Create and return the output directory path."""
    output_dir = Path("output/research_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@tool
def scrape_urls(urls: List[str], agent) -> List[Dict[str, Any]]:
    """Scrape content from a list of URLs using parallel fetching.

    Args:
        urls: List of URLs to scrape
        agent: Agent instance to execute tools

    Returns:
        List of dictionaries containing scraped content and metadata
    """
    logger.info(f"Scraping content from {len(urls)} URLs")
    
    try:
        # Use parallel fetching for efficiency
        scraped_data = agent.execute_tool(
            "custom_text_browser",
            action="fetch_parallel",
            urls=urls,
            use_proxy=True,
            random_delay=True
        )
        
        # Process and format the scraped content
        processed_data = []
        for url, content in zip(urls, scraped_data):
            processed_data.append({
                "url": url,
                "scraped_content": content,
                "scrape_time": datetime.now().isoformat()
            })
            
        return processed_data
        
    except Exception as e:
        logger.warning(f"Error during URL scraping: {str(e)}")
        return []


@tool
def enhance_research_query(research_topic: str, aspect: str) -> str:
    """Generate optimized search queries using LLM analysis."""
    prompt = f"""Create a comprehensive search query for researching:
Topic: {research_topic}
Focus Aspect: {aspect}

Include relevant keywords and search operators. Respond ONLY with the query."""
    
    try:
        # Use a simple rule-based approach instead of LLM
        enhanced = f"{research_topic} {aspect} latest developments research"
        return enhanced.strip()
    except Exception as e:
        logger.warning(f"Query enhancement failed: {str(e)}")
        return f"{research_topic} {aspect}"


@tool
def save_results(results: List[Dict[str, str]], query: str, aspect: str, output_dir: Path) -> str:
    """
    Save search results with enhanced metadata.

    Args:
        results: List of search results
        query: Search query used
        aspect: Research aspect
        output_dir: Output directory path

    Returns:
        Path to saved file
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"research_{aspect}_{timestamp}.json"
        filepath = output_dir / filename

        data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "aspect": aspect,
                "result_count": len(results)
            },
            "results": results
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(filepath)
    except Exception as e:
        raise ToolError(f"Failed to save results: {str(e)}")


@tool
def format_search_results(results: List[Dict[str, str]]) -> str:
    """Format search results in a readable way."""
    if not results:
        return "No results found"

    formatted = ["\n=== Search Results ==="]
    for i, result in enumerate(results, 1):
        formatted.extend([
            f"\nResult {i}:",
            "-" * 50,
            f"Title: {result.get('title', 'N/A')}",
            f"URL: {result.get('href', result.get('url', 'N/A'))}",
            "\nSnippet:",
            result.get('body', result.get('snippet', 'No snippet available')),
            "\nScraped Content:" if 'scraped_content' in result else "",
            (result['scraped_content'][:500] + "..." if len(result['scraped_content']) > 500 else result['scraped_content']) if 'scraped_content' in result else "",
            "-" * 50
        ])
    return "\n".join(formatted)


@tool
def generate_research_config(research_topic: str, aspects: List[str]) -> Dict[str, Dict[str, int]]:
    """Generates a research configuration dictionary with suggested max_results per aspect.

    Uses LLM analysis to determine a reasonable number of search results ('max_results') 
    to retrieve for each research aspect, considering the overall research topic.

    Args:
        research_topic: The main topic being researched.
        aspects: A list of specific aspects identified for research.

    Returns:
        A dictionary where keys are aspects and values are dictionaries containing 'max_results'.
        Example: {'market': {'max_results': 5}, 'technical': {'max_results': 7}}
        Returns an empty dictionary if generation fails.
    """
    prompt = f"""Given the research topic '{research_topic}', and the specific aspects {aspects} to investigate, determine a reasonable number of search results (max_results) to retrieve for each aspect. Consider the likely depth required for each aspect. 

    Return the configuration ONLY as a JSON dictionary where keys are the aspect names and values are dictionaries containing the 'max_results' integer. 

    Example format: {{"aspect1": {{"max_results": 5}}, "aspect2": {{"max_results": 8}}}}
    """
    
    logger.warning("Using placeholder implementation for generate_research_config")
    generated_config = {}
    for aspect in aspects:
        generated_config[aspect] = {"max_results": 5} 
    return generated_config


def register_research_tools(factory: AgentFactory) -> None:
    """Register all research tools with the factory."""
    tools = [
        interpret_research_request,
        setup_output_directory,
        enhance_research_query,
        save_results,
        format_search_results,
        generate_research_config,
        scrape_urls,
        duckduckgo_search_tool,
        get_browser_tool()
    ]

    for tool_func in tools:
        if hasattr(tool_func, '_tool'):
            factory.register_tool(tool_func._tool)
        else:
            factory.register_tool(tool_func)


def main():
    """Run the agentic research workflow."""
    try:
        factory = AgentFactory.get_instance()
        register_research_tools(factory)

        research_agent = factory.create_agent(model="deepseek/deepseek-chat")

        user_request = "research about the latest ai agent technies used by the industry"
        logger.info(f"Starting research based on user request: \"{user_request}\"")

        interpretation = research_agent.execute_tool(
            "interpret_research_request",
            request=user_request
        )
        
        research_topic = interpretation.get("topic")
        aspects_to_research = interpretation.get("aspects", [])

        if not research_topic or not aspects_to_research:
             logger.error("Failed to interpret research request. Cannot proceed.")
             return

        logger.info("Generating dynamic research configuration...")
        research_aspects_config = research_agent.execute_tool(
            "generate_research_config",
            research_topic=research_topic,
            aspects=aspects_to_research
        )

        if not research_aspects_config:
            logger.error("Failed to generate research configuration. Cannot proceed.")
            return
        
        logger.info(f"Generated config: {research_aspects_config}")

        for aspect in aspects_to_research:
            if aspect not in research_aspects_config:
                logger.warning(f"Aspect '{aspect}' was identified but missing from generated config. Skipping.")
                continue

            config = research_aspects_config[aspect]
            logger.info(f"Researching aspect '{aspect}' of topic '{research_topic}'")

            enhanced_query = research_agent.execute_tool(
                "enhance_research_query",
                research_topic=research_topic,
                aspect=aspect
            )
            logger.info(f"Generated query: {enhanced_query}")

            search_result = research_agent.execute_tool(
                "duckduckgo_search",
                keywords=enhanced_query,
                max_results=config["max_results"]
            )
            
            if isinstance(search_result, dict) and "results" in search_result:
                results = search_result["results"]
            else:
                logger.warning(f"Unexpected search result format: {search_result}")
                results = []

            output_dir = research_agent.execute_tool("setup_output_directory")

            # Extract URLs from search results
            logger.info(f"Raw search results: {results}")
            urls = [result.get('href', result.get('url', result.get('link', ''))) for result in results]
            logger.info(f"Extracted URLs before filtering: {urls}")
            urls = [url for url in urls if url and url.startswith('http')]
            logger.info(f"Final URLs after filtering: {urls}")
            
            # Only scrape if we have valid URLs
            if urls:
                # Scrape content from URLs using parallel fetching
                scraped_data = research_agent.execute_tool(
                    "custom_text_browser",
                    action="fetch_parallel",
                    urls=",".join(urls),
                    use_proxy=True,
                    random_delay=True
                )
            else:
                logger.warning("No valid URLs found to scrape")
                scraped_data = {'results': {}}
            
            # Process the scraped data
            processed_data = []
            if isinstance(scraped_data, dict) and 'results' in scraped_data:
                for url, content in scraped_data['results'].items():
                    if not content.startswith('Error:'):
                        processed_data.append({
                            'url': url,
                            'scraped_content': content,
                            'scrape_time': datetime.now().isoformat()
                        })
            
            # Enhance results with scraped content
            enhanced_results = []
            for result in results:
                enhanced_result = result.copy()
                # Find matching scraped data
                result_url = result.get('href', result.get('url', result.get('link', '')))
                for scraped in processed_data:
                    if scraped['url'] == result_url:
                        enhanced_result['scraped_content'] = scraped['scraped_content']
                        enhanced_result['scrape_time'] = scraped['scrape_time']
                        break
                enhanced_results.append(enhanced_result)
            
            output_file = research_agent.execute_tool(
                "save_results",
                results=enhanced_results,
                query=enhanced_query,
                aspect=aspect,
                output_dir=output_dir
            )

            formatted = research_agent.execute_tool(
                "format_search_results",
                results=results
            )

            logger.info(f"Research completed for {aspect}")
            logger.info(f"Results saved to: {output_file}")
            logger.info(formatted)

    except Exception as e:
        logger.error(f"Research failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
