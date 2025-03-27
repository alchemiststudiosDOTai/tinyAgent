
url = "https://huggingface.co/blog/open-deep-research"
print(f"Using text browser to visit: {url}")

# Use the text browser function directly with explicit parameters
result = custom_text_browser_function(
    url=url,
    action='visit',
    use_proxy=False,
    random_delay=True
)

# Print the result
if result:
    # Extract content from the result
    content = result.get('content', '')
    # Limit to 500 characters
    limited_content = content[:500] + \
        "..." if len(content) > 500 else content

    print("\nPage Title:", result.get('title', 'No title'))
    print("\nContent (first 500 chars):")
    print("-" * 50)
    print(limited_content)
