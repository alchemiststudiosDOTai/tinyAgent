# Creating Agents in tinyAgent Framework

This document explains the various methods to create, configure, and utilize agents in the tinyAgent framework.

## Understanding Agents in tinyAgent

In the tinyAgent framework, an agent is a flexible entity that:
- Leverages language models to understand natural language queries
- Executes tools to accomplish tasks
- Manages tool execution flow
- Handles errors and retry logic
- Respects rate limits for API calls

## Methods to Create Agents

The framework offers multiple approaches to create agents, each suited for different use cases:

### 1. Using Orchestrator (For Most Applications)

The `Orchestrator` provides a high-level interface for task submission and management, as shown in cookbook/01_basic_agent.py:

```python
from core.factory.orchestrator import Orchestrator

# Get the orchestrator singleton
orchestrator = Orchestrator.get_instance()

# Submit a task
task_id = orchestrator.submit_task("Calculate 5 + 3")

# Get the task result
status = orchestrator.get_task_status(task_id)
result = status.result
print(f"\nResult: {result}")
```

### 2. Using AgentFactory (Direct Access)

The `AgentFactory` gives you more direct control when you need it, as shown in cookbook/06_text_browser.py:

```python
from core.factory.agent_factory import AgentFactory
from core.tools.custom_text_browser import get_tool

# Get the factory singleton
factory = AgentFactory.get_instance()

# Register tools with the factory
factory.register_tool(get_tool())

# Create an agent with access to registered tools
agent = factory.create_agent()

# Use the agent
result = agent.run(
    "Use text browser to visit webpage",
    variables={
        "action": "visit",
        "path_or_uri": "https://example.com",
        "use_proxy": False,
        "random_delay": True
    }
)
```

### 3. Dynamic Agent Creation (For Specialized Tasks)

When you need an agent with specialized capabilities:

```python
from core.factory.dynamic_agent_factory import DynamicAgentFactory

# Get the dynamic factory
factory = DynamicAgentFactory.get_instance()

# Create a specialized agent
agent_result = factory.create_agent_from_requirement(
    "I need an agent that can analyze protein sequences"
)

if agent_result["success"]:
    agent = agent_result["agent"]
    result = agent.run("Analyze this protein sequence...")
```

## Agent Execution Methods

Once you have an agent, you can interact with it in several ways:

### 1. Running Queries

The simplest approach is to run a natural language query:

```python
result = agent.run("Find information about Python programming")
```

### 2. Direct Tool Execution

You can explicitly call a specific tool, as demonstrated in cookbook/09_research.py:

```python
# Enhanced query
enhanced_query = agent.execute_tool(
    "enhance_research_query",
    base_query="Python programming",
    aspect="technical"
)

# Perform search
search_result = agent.execute_tool(
    "duckduckgo_search",
    keywords=enhanced_query,
    max_results=5
)
```

### 3. Structured Task Execution

For more complex tasks with structured data:

```python
result = agent.run(
    "Search for information about Python",
    variables={
        "search_term": "Python programming language",
        "max_results": 5,
        "detailed": True
    }
)
```

## Tool Registration

Agents use tools to perform tasks. There are several ways to register tools:

### 1. With the Factory

```python
# Register a tool function
factory.create_tool(
    name="echo",
    description="Echoes the input text",
    func=echo_message
)

# Register an existing Tool object
factory.register_tool(my_tool)
```

### 2. Using Decorators

As shown in cookbook/09_research.py:

```python
from core.decorators import tool

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
        "technical": "implementation code tutorial examples",
        "business": "market industry companies commercial"
    }
    return f"{base_query} {research_aspects.get(aspect, '')}"
```

### 3. When Creating an Agent

```python
agent = Agent(tools=[tool1, tool2, tool3])
```

## Handling Tool Results

When working with tools, you may need to process their results:

```python
# When tools might return metadata alongside results
search_result = agent.execute_tool(
    "duckduckgo_search",
    keywords=enhanced_query,
    max_results=5
)

# Extract the actual results if needed
if isinstance(search_result, dict) and "results" in search_result:
    results = search_result["results"]
else:
    results = []
```

## Agent Configuration

You can configure agents through the factory or directly:

```python
# Configure through factory
factory.config["model"] = "deepseek/deepseek-chat"
agent = factory.create_agent()

# Or when creating an agent
agent = factory.create_agent(model="anthropic/claude-3-opus")
```

## Real-World Example: Research Agent

Here's a complete example of a research agent based on cookbook/09_research.py:

```python
from core.factory.agent_factory import AgentFactory
from core.tools.duckduckgo_search import duckduckgo_search_tool
from core.decorators import tool
from typing import Dict, List

# Create custom tools
@tool
def setup_output_directory():
    """Create and return the output directory path."""
    output_dir = Path("output/research_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

@tool
def enhance_research_query(base_query: str, aspect: str = "") -> str:
    """Enhance search query with aspect-specific terms."""
    research_aspects = {
        "technical": "implementation code tutorial examples",
        "business": "market industry companies commercial"
    }
    return f"{base_query} {research_aspects.get(aspect, '')}"

@tool
def format_search_results(results: List[Dict[str, str]]) -> str:
    """Format search results for readability."""
    if not results:
        return "No results found"

    formatted = ["\n=== Search Results ==="]
    for i, result in enumerate(results, 1):
        formatted.extend([
            f"\nResult {i}:",
            f"Title: {result.get('title', 'N/A')}",
            f"URL: {result.get('href', 'N/A')}",
            f"Snippet: {result.get('body', 'No snippet available')}"
        ])
    return "\n".join(formatted)

# Set up the agent
factory = AgentFactory.get_instance()
factory.register_tool(duckduckgo_search_tool)
factory.register_tool(enhance_research_query._tool)  # Note ._tool for decorated functions
factory.register_tool(format_search_results._tool)
factory.register_tool(setup_output_directory._tool)

# Create the agent
agent = factory.create_agent()

# Execute research workflow
enhanced_query = agent.execute_tool(
    "enhance_research_query",
    base_query="Python programming",
    aspect="technical"
)

search_result = agent.execute_tool(
    "duckduckgo_search",
    keywords=enhanced_query,
    max_results=5
)

# Extract the actual results from the response
if isinstance(search_result, dict) and "results" in search_result:
    results = search_result["results"]
else:
    results = []

# Setup output directory
output_dir = agent.execute_tool("setup_output_directory")

# Format and display results
formatted = agent.execute_tool(
    "format_search_results",
    results=results
)
print(formatted)
```

## Best Practices

1. **Choose the Right Creation Method**:
   - Use `Orchestrator.get_instance()` for complex workflows with potential handoffs
   - Use `factory.create_agent()` when you need more direct control
   - Use dynamic agent creation for specialized, on-demand capabilities

2. **Register Tools Appropriately**:
   - Centralize tool registration with the factory when possible
   - Use the `@tool` decorator for simple function-based tools
   - Remember to use `function._tool` when registering decorated tools

3. **Handle Results Carefully**:
   - Always check the format of tool results
   - Some tools return dictionaries with nested results, others return direct values
   - Extract results from metadata as needed

4. **Consider Execution Flow**:
   - Chain tools together when needed by passing results between them
   - Use structured variables for complex inputs
   - Leverage the agent's reasoning capabilities for determining the right tools to use

## Troubleshooting

Common issues and solutions:

1. **AttributeError: 'function' object has no attribute 'name'**: Remember to use `function._tool` when registering a decorated function
2. **TypeError: Agent.execute_tool() missing argument 'tool_name'**: The first argument to execute_tool must be the tool name
3. **String vs Dictionary Results**: Some tools return dictionaries with a "results" key, others return direct results 
