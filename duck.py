from tiny_agent import tool, tiny_agent


@tool
def search_web(query: str) -> str:
    """DuckDuckGo search and return first snippet."""
    ...


agent = tiny_agent(tools=[search_web])
print(agent.run("Who coined 'simplicity scales'?"))
