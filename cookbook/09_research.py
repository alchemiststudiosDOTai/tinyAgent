#!/usr/bin/env python3
"""
Agentic Research Workflow using TinyAgent Framework

Features:
1. Proper tool-based architecture
2. Framework-compatible error handling
3. Configurable through AgentFactory
4. Integrated with core tooling
"""



from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import json
import os
import sys

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.factory.agent_factory import AgentFactory
from core.tools.duckduckgo_search import duckduckgo_search_tool
from core.decorators import tool
from core.exceptions import ToolError
from core.logging import get_logger

#


logger = get_logger(__name__)


@tool
def interpret_research_request(request: str) -> Dict[str, any]:
    """
    Interprets a natural language research request to extract the topic and relevant aspects.

    Args:
        request: The natural language research request (e.g., "research the kratom industry and safety").

    Returns:
        A dictionary containing the identified 'topic' (str) and 'aspects' (list of str).
    """
    logger.info(f"Interpreting research request: \"{request}\"")
    request_lower = request.lower()
    
    # Predefined aspect keywords and their mapping
    # Simple keyword matching for now. Could be enhanced with NLP libraries or LLM calls.
    aspect_mapping = {
        "substance": ["substance", "chemical", "composition", "effects", "uses"],
        "market": ["market", "vendors", "suppliers", "distribution", "statistics", "analysis", "industry", "business"],
        "legal": ["legal", "law", "laws", "regulation", "compliance", "policy", "fda"],
        "safety": ["safety", "safe", "side effects", "clinical trials", "risks", "danger"],
        "production": ["production", "manufacturing", "process", "quality", "standards", "certification"]
    }

    identified_aspects = set()
    potential_topic_words = request_lower.split()

    for aspect_key, keywords in aspect_mapping.items():
        for keyword in keywords:
            if keyword in request_lower:
                identified_aspects.add(aspect_key)
                # Remove aspect-related keywords from potential topic words
                potential_topic_words = [word for word in potential_topic_words if keyword not in word] # Simple word removal

    # If no specific aspects identified, use a default set
    if not identified_aspects:
        identified_aspects = {"substance", "market", "safety"}
        logger.info("No specific aspects identified in request, using defaults.")

    # Basic topic extraction: Assume the longest remaining word sequence is the topic.
    # Remove common filler words. This is a basic heuristic.
    filler_words = {"research", "about", "the", "and", "its", "tell", "me", "find", "information", "on"}
    topic_words = [word for word in potential_topic_words if word not in filler_words]
    topic = " ".join(topic_words).strip()

    # Fallback topic if extraction fails
    if not topic:
        topic = "kratom" # Default topic if extraction fails badly
        logger.warning("Could not reliably extract topic, defaulting to 'kratom'.")
    
    logger.info(f"Identified Topic: '{topic}', Aspects: {list(identified_aspects)}")
    
    return {"topic": topic, "aspects": list(identified_aspects)}


@tool
def setup_output_directory() -> Path:
    """Create and return the output directory path."""
    output_dir = Path("output/research_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@tool
def enhance_research_query(research_topic: str, aspect: str) -> str:
    """
    Enhance search query with aspect-specific terms.

    Args:
        research_topic: The core topic to research
        aspect: Research aspect to focus on

    Returns:
        Enhanced query string
    """
    research_aspects = {
        "substance": "chemical composition effects uses research studies",
        "market": "market size vendors suppliers distribution statistics analysis",
        "legal": "legal status regulation compliance requirements FDA policy",
        "safety": "safety studies side effects research clinical trials risks",
        "production": "manufacturing process quality control standards certification"
    }

    if aspect and aspect in research_aspects:
        return f"{research_topic} {research_aspects[aspect]}"
    return research_topic # Return the base topic if aspect is not found or not provided


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
            "-" * 50
        ])
    return "\n".join(formatted)


def register_research_tools(factory: AgentFactory) -> None:
    """Register all research tools with the factory."""
    tools = [
        interpret_research_request,
        setup_output_directory,
        enhance_research_query,
        save_results,
        format_search_results,
        duckduckgo_search_tool
    ]

    for tool_func in tools:
        # If it's a decorated function, get the Tool instance from _tool attribute
        if hasattr(tool_func, '_tool'):
            factory.register_tool(tool_func._tool)
        # If it's already a Tool instance, register it directly
        else:
            factory.register_tool(tool_func)


def main():
    """Run the agentic research workflow."""
    try:
        # Initialize agent factory
        factory = AgentFactory.get_instance()
        register_research_tools(factory)

        # Create research agent
        research_agent = factory.create_agent(model="deepseek/deepseek-chat")

        # --- New: Define research request using natural language ---
        user_request = "research about the kratom industry and its safety"
        logger.info(f"Starting research based on user request: \"{user_request}\"")

        # --- New: Interpret the request ---
        interpretation = research_agent.execute_tool(
            "interpret_research_request",
            request=user_request
        )
        
        research_topic = interpretation.get("topic")
        aspects_to_research = interpretation.get("aspects", [])

        if not research_topic or not aspects_to_research:
             logger.error("Failed to interpret research request. Cannot proceed.")
             return

        # Research configuration specifying aspects and result limits
        # This config now mainly provides max_results per known aspect
        research_aspects_config = {
            "substance": { "max_results": 5 },
            "market": { "max_results": 3 },
            "legal": { "max_results": 3 }, # Added legal for completeness
            "safety": { "max_results": 4 },
            "production": { "max_results": 2 } # Added production for completeness
        }

        # Execute research workflow for each identified aspect
        for aspect in aspects_to_research:
            if aspect not in research_aspects_config:
                logger.warning(f"Aspect '{aspect}' identified but not found in config. Skipping.")
                continue

            config = research_aspects_config[aspect]
            logger.info(f"Researching aspect '{aspect}' of topic '{research_topic}'")

            # Generate enhanced query using the topic and aspect
            enhanced_query = research_agent.execute_tool(
                "enhance_research_query",
                research_topic=research_topic,
                aspect=aspect
            )
            logger.info(f"Generated query: {enhanced_query}")

            # Perform search
            search_result = research_agent.execute_tool(
                "duckduckgo_search",
                keywords=enhanced_query,
                max_results=config["max_results"]
            )
            
            # Extract the actual results list from the response
            if isinstance(search_result, dict) and "results" in search_result:
                results = search_result["results"]
            else:
                logger.warning(f"Unexpected search result format: {search_result}")
                results = []

            # Setup output
            output_dir = research_agent.execute_tool("setup_output_directory")

            # Save results
            output_file = research_agent.execute_tool(
                "save_results",
                results=results,
                query=enhanced_query,
                aspect=aspect,
                output_dir=output_dir
            )

            # Format results
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
