import asyncio
from dotenv import load_dotenv
import os
from core.tools.business_deepsearch import BusinessDeepSearch
from core.config import load_config
import aiohttp

def format_proxy_url():
    """Format proxy URL using environment variables."""
    load_dotenv()  # Load environment variables from .env file
    
    username = os.getenv('TINYAGENT_PROXY_USERNAME')
    password = os.getenv('TINYAGENT_PROXY_PASSWORD')
    country = os.getenv('TINYAGENT_PROXY_COUNTRY', 'us')
    
    if not all([username, password]):
        return None
        
    return f"http://customer-{username}-cc-{country}:{password}@pr.oxylabs.io:7777"

def configure_proxy_session(session):
    """Configure proxy settings for an aiohttp session."""
    proxy_url = format_proxy_url()
    if proxy_url:
        session.proxy = proxy_url
        print(f"Configured proxy URL: {proxy_url.replace(os.getenv('TINYAGENT_PROXY_PASSWORD', ''), '********')}")
    else:
        print("No proxy configuration found - continuing without proxy")
    return session

async def main():
    """Main function to run the business search."""
    search_term = "kratom market size"
    max_results = 1
    
    # Create a session with proxy configuration
    session = aiohttp.ClientSession()
    session = configure_proxy_session(session)
    
    try:
        async with BusinessDeepSearch() as searcher:
            # Use the configured session
            searcher.session = session
            
            results = await searcher.search(
                query=search_term,
                max_results=max_results
            )
            
            print(f"\nSearch Results for '{search_term}':")
            print("-" * 80)
            
            for i, result in enumerate(results, 1):
                print(f"\nResult {i}:")
                print(f"Title: {result.get('title', 'N/A')}")
                print(f"URL: {result.get('url', 'N/A')}")
                print(f"Snippet: {result.get('snippet', 'N/A')}")
                print("-" * 40)
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())
