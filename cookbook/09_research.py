#!/usr/bin/env python3
"""
Enhanced Business Research Tool with Advanced Proxy Support

Features:
1. Multiple proxy support (Tor, rotating proxies, direct)
2. Advanced error handling and retries
3. Configurable search parameters
4. Enhanced data storage
5. Rate limiting protection
"""

import os
import sys
import json
import time
import random
import urllib.request
from typing import Optional, Dict, List, Generator
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import (
    DuckDuckGoSearchException,
    RatelimitException,
    TimeoutException,
)

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factory.agent_factory import AgentFactory
from core.tools.duckduckgo_search import duckduckgo_search_tool, perform_duckduckgo_search

@dataclass
class ProxyConfig:
    """Proxy configuration settings."""
    enabled: bool
    url_template: str
    username: Optional[str] = None
    password: Optional[str] = None
    country: str = "US"
    
    @classmethod
    def from_config(cls) -> 'ProxyConfig':
        """Create proxy config from config.yml."""
        load_dotenv()
        
        try:
            import yaml
            with open('config.yml', 'r') as f:
                config = yaml.safe_load(f)
            
            proxy_config = config.get('proxy', {})
            
            if not proxy_config.get('enabled', False):
                return cls(enabled=False, url_template="")
            
            return cls(
                enabled=True,
                url_template=proxy_config.get('url', ''),
                username=os.getenv('TINYAGENT_PROXY_USERNAME'),
                password=os.getenv('TINYAGENT_PROXY_PASSWORD'),
                country=os.getenv('TINYAGENT_PROXY_COUNTRY', 'US')
            )
        except Exception as e:
            print(f"Warning: Failed to load proxy config: {str(e)}")
            return cls(enabled=False, url_template="")
    
    def get_proxy_string(self) -> Optional[str]:
        """Get formatted proxy string using the URL template."""
        if not self.enabled or not self.url_template:
            return None
            
        if not all([self.username, self.password]):
            print("Warning: Proxy credentials not found in environment variables")
            return None
            
        try:
            # Format the URL template with credentials
            proxy_url = self.url_template % (
                self.username,
                self.country,
                self.password
            )
            return proxy_url
        except Exception as e:
            print(f"Warning: Failed to format proxy URL: {str(e)}")
            return None

    def get_proxy_handler(self) -> Optional[urllib.request.ProxyHandler]:
        """Get configured proxy handler for urllib."""
        proxy_url = self.get_proxy_string()
        if not proxy_url:
            return None
        
        return urllib.request.ProxyHandler({
            'http': proxy_url,
            'https': proxy_url
        })

class ResearchManager:
    """Manages research operations with proxy support and error handling."""
    
    def __init__(self, proxy_config: ProxyConfig):
        self.proxy_config = proxy_config
        self.ddgs = None
        self.last_rotation = time.time()
        self.initialize_ddgs()
    
    def initialize_ddgs(self):
        """Initialize or reinitialize the DDGS client."""
        proxy = self.proxy_config.get_proxy_string()
        self.ddgs = DDGS(
            proxy=proxy,
            timeout=20
        )
        self.last_rotation = time.time()
    
    def should_rotate_proxy(self) -> bool:
        """Check if it's time to rotate the proxy."""
        if not self.proxy_config.enabled:
            return False
        # Rotate every 60 seconds if proxy is enabled
        return time.time() - self.last_rotation >= 60

    def search_with_retries(
        self,
        keywords: str,
        region: str = "wt-wt",
        safesearch: str = "moderate",
        timelimit: Optional[str] = None,
        backend: str = "auto",
        max_results: Optional[int] = None,
        max_retries: int = 3,
        retry_delay: int = 5
    ) -> List[Dict[str, str]]:
        """
        Perform search with automatic retries and proxy rotation.
        
        Args:
            keywords: Search query
            region: Search region (e.g., 'wt-wt', 'us-en')
            safesearch: SafeSearch setting ('on', 'moderate', 'off')
            timelimit: Time limit for results ('d', 'w', 'm', 'y')
            backend: Search backend ('auto', 'html', 'lite')
            max_results: Maximum number of results to return
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            List of search results
        """
        attempts = 0
        while attempts < max_retries:
            try:
                if self.should_rotate_proxy():
                    self.initialize_ddgs()
                
                results = list(self.ddgs.text(
                    keywords=keywords,
                    region=region,
                    safesearch=safesearch,
                    timelimit=timelimit,
                    backend=backend,
                    max_results=max_results
                ))
                
                return results
                
            except RatelimitException:
                print(f"Rate limit hit on attempt {attempts + 1}/{max_retries}")
                if self.proxy_config.enabled:
                    self.initialize_ddgs()
                time.sleep(retry_delay * (attempts + 1))
                
            except TimeoutException:
                print(f"Timeout on attempt {attempts + 1}/{max_retries}")
                time.sleep(retry_delay)
                
            except DuckDuckGoSearchException as e:
                print(f"Search error on attempt {attempts + 1}/{max_retries}: {str(e)}")
                if attempts == max_retries - 1:
                    raise
                time.sleep(retry_delay)
                
            attempts += 1
        
        raise DuckDuckGoSearchException(f"Failed after {max_retries} attempts")

def setup_output_directory() -> Path:
    """Create and return the output directory path."""
    output_dir = Path("output/research_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

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

def format_search_results(results: list) -> None:
    """Format and print search results in a readable way."""
    if not results:
        print("No results found")
        return

    print("\n=== Search Results ===")
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print("-" * 50)
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"URL: {result.get('url', 'N/A')}")
        print("\nSnippet:")
        print(result.get('snippet', 'No snippet available'))
        print("-" * 50)

def main():
    """Run the enhanced research tool."""
    # Setup
    output_dir = setup_output_directory()
    proxy_config = ProxyConfig.from_config()
    research_mgr = ResearchManager(proxy_config)
    
    # Research configuration
    research_config = {
        "substance": {
            "query": "starts ups in USA",
            "max_results": 10
        },
     
    }
    
    print("Enhanced Research Tool")
    print("====================")
    print(f"Proxy enabled: {proxy_config.enabled}")
    if proxy_config.enabled:
        print(f"Using proxy with country: {proxy_config.country}")
    print(f"Output directory: {output_dir}")
    print()
    
    all_results = {}
    
    # Run research for each aspect
    for aspect, config in research_config.items():
        print(f"\nResearching {aspect.upper()}")
        print("-" * 50)
        
        try:
            # Enhance the query with aspect-specific terms
            enhanced_query = enhance_research_query(config["query"], aspect)
            print(f"Enhanced query: {enhanced_query}")
            
            # Perform the search with retries and proxy rotation
            results = research_mgr.search_with_retries(
                keywords=enhanced_query,
                max_results=config["max_results"],
                region="us-en",
                safesearch="moderate",
                timelimit="y",
                backend="auto"
            )
            
            # Save results
            output_file = save_results(
                results=results,
                query=enhanced_query,
                aspect=aspect,
                output_dir=output_dir
            )
            
            print(f"Found {len(results)} results")
            print(f"Saved to: {output_file}")
            
            all_results[aspect] = {
                "query": enhanced_query,
                "results": results,
                "output_file": output_file
            }
            
        except DuckDuckGoSearchException as e:
            print(f"Error researching {aspect}: {str(e)}")
            continue
        
        except Exception as e:
            print(f"Unexpected error researching {aspect}: {str(e)}")
            continue
    
    # Print summary
    print("\nResearch Summary")
    print("===============")
    for aspect, data in all_results.items():
        print(f"\n{aspect.upper()}:")
        print(f"- Results: {len(data['results'])}")
        print(f"- Output: {data['output_file']}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nResearch interrupted by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)
