import urllib.request
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get proxy credentials from environment
username = os.getenv('TINYAGENT_PROXY_USERNAME')
password = os.getenv('TINYAGENT_PROXY_PASSWORD')
country = os.getenv('TINYAGENT_PROXY_COUNTRY', 'US')

if not all([username, password]):
    print("Error: Missing proxy credentials in .env file")
    print("Required variables:")
    print("- TINYAGENT_PROXY_USERNAME")
    print("- TINYAGENT_PROXY_PASSWORD")
    print("- TINYAGENT_PROXY_COUNTRY (optional, defaults to US)")
    exit(1)

# Format proxy URL
proxy_url = f'http://customer-{username}-cc-{country}:{password}@pr.oxylabs.io:7777'

# Create proxy handler
proxy_handler = urllib.request.ProxyHandler({
    'http': proxy_url,
    'https': proxy_url,
})

# Build opener with proxy
opener = urllib.request.build_opener(proxy_handler)

try:
    print(f"\nTesting proxy connection...")
    print(f"Proxy URL: {proxy_url.replace(password, '********')}")
    
    # Test connection to ip.oxylabs.io
    response = opener.open('https://ip.oxylabs.io/location')
    result = response.read()
    print("\nProxy test successful!")
    print("Response:", result.decode())
    
except Exception as e:
    print("\nProxy test failed!")
    print("Error:", str(e))