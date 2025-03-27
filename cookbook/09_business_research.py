#!/usr/bin/env python3
"""
Example 9: Business Research Agent

Demonstrates an agent that combines search and browsing tools to research companies,
saving both structured and unstructured data with configurable search depth.
"""

import os
import sys
import json
import re
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import Agent
from core.factory.agent_factory import AgentFactory
from core.factory.orchestrator import Orchestrator
from core.tools.duckduckgo_search import duckduckgo_search_tool
from core.tools.custom_text_browser import custom_text_browser_tool
from core.logging import get_logger

logger = get_logger(__name__)

class BusinessResearchAgent:
    """Agent that performs business research with configurable depth."""
    
    def __init__(self, max_depth: int = 2):
        self.max_depth = max_depth
        self.visited_urls = set()
        self.research_data = []
        
        # Create output directories
        self.raw_data_dir = "./business_research/raw"
        self.structured_data_dir = "./business_research/structured"
        os.makedirs(self.raw_data_dir, exist_ok=True)
        os.makedirs(self.structured_data_dir, exist_ok=True)

    def research_company(self, query: str) -> Dict[str, Any]:
        """Main research method that coordinates search and browsing."""
        try:
            # Initial search
            search_results = self._perform_search(query)
            
            # Process results with browsing
            structured_data = []
            for result in search_results[:3]:  # Limit to top 3 results for demo
                company_data = self._browse_and_extract(result['url'], depth=self.max_depth)
                if company_data:
                    structured_data.append(company_data)
                    
                    # Save both data types
                    self._save_data(
                        raw_content=company_data.pop('raw_content', ''),
                        structured_data=company_data
                    )
            
            return {
                "query": query,
                "results_found": len(structured_data),
                "companies": structured_data
            }
            
        except Exception as e:
            logger.error(f"Research failed: {str(e)}")
            return {"error": str(e)}

    def _perform_search(self, query: str) -> List[Dict[str, str]]:
        """Use DuckDuckGo search tool to find initial results."""
        search_result = duckduckgo_search_tool.func(
            keywords=query,
            max_results=5,
            safesearch="moderate"
        )
        return search_result.get('results', [])

    def _browse_and_extract(self, url: str, depth: int = 2) -> Dict[str, Any]:
        """Browse a URL and extract business information."""
        if depth == 0 or url in self.visited_urls:
            return {}
            
        self.visited_urls.add(url)
        
        try:
            # Get page content
            page_data = custom_text_browser_tool.func(
                action="visit",
                url=url,
                use_proxy=True
            )
            
            # Extract structured data
            company_info = self._extract_company_info(page_data['content'])
            company_info['source_url'] = url
            company_info['raw_content'] = page_data['content'][:1000] + "..."  # Store snippet
            
            # Follow links if depth allows
            if depth > 1:
                links = [link['url'] for link in page_data.get('links', [])][:2]  # Follow first 2 links
                for link in links:
                    subsidiary_info = self._browse_and_extract(link, depth-1)
                    if subsidiary_info:
                        company_info.setdefault('subsidiaries', []).append(subsidiary_info)
            
            return company_info
            
        except Exception as e:
            logger.warning(f"Failed to process {url}: {str(e)}")
            return {}

    def _extract_company_info(self, content: str) -> Dict[str, str]:
        """Simple pattern-based information extraction."""
        # This is a simplified example - would use LLM or more advanced NLP in real implementation
        return {
            "name": self._extract_pattern(r"Company[\s\:]+(.+?)\n", content),
            "website": self._extract_pattern(r"Website[\s\:]+(.+?)\n", content),
            "phone": self._extract_pattern(r"Phone[\s\:]+(.+?)\n", content),
            "email": self._extract_pattern(r"Email[\s\:]+(.+?)\n", content),
            "address": self._extract_pattern(r"Address[\s\:]+(.+?)\n", content)
        }

    def _extract_pattern(self, pattern: str, text: str) -> str:
        """Helper function for pattern matching."""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _save_data(self, raw_content: str, structured_data: Dict[str, Any]) -> None:
        """Save both data formats with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw content
        raw_path = os.path.join(self.raw_data_dir, f"{timestamp}.txt")
        with open(raw_path, 'w') as f:
            f.write(raw_content)
            
        # Save structured data
        struct_path = os.path.join(self.structured_data_dir, f"{timestamp}.json")
        with open(struct_path, 'w') as f:
            json.dump(structured_data, f, indent=2)

def main():
    """Create and run the business research agent."""
    # Initialize components
    factory = AgentFactory.get_instance()
    orchestrator = Orchestrator.get_instance()
    
    # Register required tools
    factory.register_tool(duckduckgo_search_tool)
    factory.register_tool(custom_text_browser_tool)
    
    # Create research agent
    research_agent = BusinessResearchAgent(max_depth=2)
    
    # Example query
    query = "tech startups in Berlin"
    print(f"Researching: {query}")
    
    # Perform research
    results = research_agent.research_company(query)
    
    # Print results
    print("\nResearch Results:")
    print(json.dumps(results, indent=2))
    
    print(f"\nData saved in:")
    print(f"- Raw data: {research_agent.raw_data_dir}")
    print(f"- Structured data: {research_agent.structured_data_dir}")

if __name__ == "__main__":
    main()
