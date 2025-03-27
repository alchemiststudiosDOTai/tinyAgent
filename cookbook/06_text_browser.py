from core.agent import Agent
from core.factory.agent_factory import AgentFactory
from core.tools.custom_text_browser import custom_text_browser_function

factory = AgentFactory.get_instance()
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
    limited_content = (content[:500] + "...") if len(content) > 500 else content

    print("\nPage Title:", result.get('title', 'No title'))
    print("\nContent (first 500 chars):")
    print("-" * 50)
    print(limited_content)
== == == =

# Create agent components
factory = AgentFactory.get_instance()
factory.register_tool(custom_text_browser_function)
agent = Agent(factory=factory)

# Execute through agent
url = "https://huggingface.co/blog/open-deep-research"
result = agent.run(
    f"Use text browser to visit: {url} with no proxy and random delays",
    variables={
        "action": "visit",
        "use_proxy": False,
        "random_delay": True
    }
)

# Process and display results
if result and 'content' in result:
    content = result['content']
    limited_content = content[:500] + "..." if len(content) > 500 else content

    print("\nPage Title:", result.get('title', 'No title'))
    print("\nContent (first 500 chars):")
    print("-" * 50)
    print(limited_content)
