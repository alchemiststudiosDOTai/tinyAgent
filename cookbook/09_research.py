#!/usr/bin/env python3
"""
Agentic Research Workflow using TinyAgent Framework

Features:
1. Proper tool-based architecture
2. Framework-compatible error handling
3. Configurable through AgentFactory
4. Integrated with core tooling
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.factory.agent_factory import AgentFactory
from core.tools.duckduckgo_search import perform_duckduckgo_search
from core.decorators import tool
from core.exceptions import ToolError
from core.logging import get_logger

logger = get_logger(__name__)

@tool
def setup_output_directory() -> Path:
    """Create and return the output directory path."""
    output_dir = Path("output/research_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

@tool
def enhance_research_query(base_query: str, aspect: str = "") -> str:
    """
    Enhance search query with aspect-specific terms.
    
    Args:
        base_query: Base search query
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
        return f"{base_query} {research_aspects[aspect]}"
    return base_query

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
            f"URL: {result.get('url', 'N/A')}",
            "\nSnippet:",
            result.get('snippet', 'No snippet available'),
            "-" * 50
        ])
    return "\n".join(formatted)

def register_research_tools(factory: AgentFactory) -> None:
    """Register all research tools with the factory."""
    tools = [
        setup_output_directory,
        enhance_research_query,
        save_results,
        format_search_results,
        perform_duckduckgo_search
    ]
    
    for tool_func in tools:
        factory.register_tool(tool_func)

def main():
    """Run the agentic research workflow."""
    try:
        # Initialize agent factory
        factory = AgentFactory.get_instance()
        register_research_tools(factory)
        
        # Create research agent
        research_agent = factory.create_agent(
            model="gpt-4",
            max_retries=3
        )
        
        # Research configuration
        research_config = {
            "substance": {
                "query": "python programming",
                "max_results": 5
            },
            "market": {
                "query": "python jobs",
                "max_results": 3
            }
        }
        
        # Execute research workflow
        for aspect, config in research_config.items():
            logger.info(f"Researching {aspect}")
            
            # Enhanced query
            enhanced_query = research_agent.execute_tool(
                "enhance_research_query",
                base_query=config["query"],
                aspect=aspect
            )
            
            # Perform search
            results = research_agent.execute_tool(
                "perform_duckduckgo_search",
                keywords=enhanced_query,
                max_results=config["max_results"]
            )
            
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
