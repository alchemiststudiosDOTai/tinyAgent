# tinyAgent: How to Cook with AI Agents

This guide provides an in-depth walkthrough of the tinyAgent framework and how to effectively use it to create AI-powered applications.

## Table of Contents

1. [Introduction](#introduction)
2. [Framework Architecture](#framework-architecture)
3. [Cookbook Examples](#cookbook-examples)
   - [Basic Agent](#1-basic-agent)
   - [Factory Agent](#2-factory-agent)
   - [Decorator Agent](#3-decorator-agent)
   - [Dynamic Agent](#4-dynamic-agent)
   - [MCP Orchestration](#5-mcp-orchestration)
4. [Building with tinyAgent](#building-with-tinyagent)
5. [Best Practices](#best-practices)

## Introduction

tinyAgent is a lightweight yet powerful framework designed to simplify the creation and management of LLM-powered agents. It allows you to quickly create specialized agents that can leverage a variety of tools to accomplish complex tasks.

Key features of the framework include:
- **Tool-based approach**: Define reusable tools that agents can utilize
- **Multiple agent creation patterns**: From simple to highly dynamic
- **Centralized tool management**: Through factory pattern
- **Rate limiting and monitoring**: Built-in usage tracking
- **Orchestration capabilities**: Coordinate multiple specialized agents
- **MCP integration**: Connect to external services and APIs

## Framework Architecture

The tinyAgent framework has several core components:

1. **Agent**: The central component that interacts with the LLM to select and execute tools based on queries.

2. **Tool**: Represents a specific capability that agents can use. Each tool has:
   - A name
   - A description
   - Parameter definitions
   - An implementation function

3. **AgentFactory**: Manages tool registration and creation, enforces rate limits.

4. **DynamicAgentFactory**: Extends the factory to analyze tasks and create specialized agents on-the-fly.

5. **Orchestrator**: Coordinates multiple agents to handle complex workflows.

6. **MCP Integration**: Connects to the Model Context Protocol for external API access.

## Cookbook Examples

### 1. Basic Agent

File: `01_basic_agent.py`

The simplest approach to using tinyAgent. This example demonstrates:
- Basic tool creation through the factory
- Single agent with a calculator tool
- Direct execution of a query

```python
# Get the singleton factory instance
factory = AgentFactory.get_instance()

# Create calculator tool
factory.create_tool(
    name="calculator",
    description="Perform basic arithmetic operations",
    func=calculate
)

# Create an agent with the factory
agent = Agent(factory=factory)

# Run the agent with a query
result = agent.run("Calculate 5 + 3")
```

This pattern is ideal for simple applications with a limited set of tools.

### 2. Factory Agent

File: `02_factory_agent.py`

Demonstrates using the AgentFactory to manage multiple tools and track usage:
- Centralized tool registration
- Tool usage statistics
- Multiple tool execution

```python
# Register multiple tools with the factory
factory.create_tool(
    name="calculator",
    description="Perform arithmetic operations",
    func=calculate
)

factory.create_tool(
    name="echo",
    description="Echo back messages",
    func=echo_message
)

# Run multiple queries
for query in queries:
    result = agent.run(query)
    
# Get usage statistics
status = factory.get_status()
```

This pattern is useful when you need centralized tool management and monitoring across your application.

### 3. Decorator Agent

File: `03_decorator_agent.py`

Shows a more concise way to define tools using decorators:
- Simplified tool creation through decorators
- Automatic type inference from Python type hints
- Optional parameters with default values
- Rate limiting through decorator parameters

```python
@tool
def format_text(text: str) -> str:
    """Format text with proper capitalization and punctuation."""
    formatted = text.strip().capitalize()
    if not formatted.endswith(('.', '!', '?')):
        formatted += '.'
    return formatted

@tool(rate_limit=5)
def reverse_text(text: str) -> str:
    """Reverse the characters in a text string."""
    return text[::-1]
```

Register decorated tools with the factory:
```python
factory.register_tool(format_text._tool)
factory.register_tool(reverse_text._tool)
```

This pattern provides a clean, Pythonic way to define tools, improving code readability and maintainability.

### 4. Dynamic Agent

File: `04_dynamic_agent.py`

Demonstrates dynamic agent creation based on task requirements:
- Task analysis to determine required tools
- Automatic tool selection
- Creating specialized agents for different tasks

```python
# Create the dynamic agent factory
factory = DynamicAgentFactory.get_instance()

# Register various tools
register_text_tools(factory)
register_math_tools(factory)
register_utility_tools(factory)

# Create a specialized agent for text processing
text_agent = factory.create_dynamic_agent("I need to analyze text data")

# Create a specialized agent for math
math_agent = factory.create_dynamic_agent("I need to perform calculations")
```

This pattern is powerful when building systems that need to adapt to different types of requests or user intents.

### 5. MCP Orchestration

File: `05_mcp_orchestration.py`

A comprehensive example showcasing complex orchestration with MCP integration:
- Web search through the Brave Search API
- Multiple specialized agents working together
- Task delegation and coordination
- Context passing between agents
- Structured report generation

```python
# Get the orchestrator
orchestrator = Orchestrator.get_instance()

# Register MCP tools like Brave Search
factory.register_tool(brave_web_search_tool)

# Register specialized research tools
register_research_tools(factory)

# Submit a complex task to the orchestrator
task_id = orchestrator.submit_task(
    "Research 'AI in healthcare' and generate a report",
    need_permission=False
)

# Check task status
task_status = orchestrator.get_task_status(task_id)
```

This pattern is suitable for complex applications that require multiple specialized agents to collaborate on sophisticated workflows.

## Building with tinyAgent

The tinyAgent framework can be used to build a wide variety of applications:

### 1. Research Assistants
Create agents that can search the web, analyze information, and generate reports on specific topics.

```python
# Research assistant using MCP orchestration
research_agent = factory.create_agent(tools=[
    brave_web_search_tool,
    analyze_text_tool,
    generate_report_tool
])
```

### 2. Data Analysis Tools
Build agents that process, transform, and analyze data.

```python
# Data analysis agent
analysis_agent = factory.create_agent(tools=[
    load_csv_tool,
    filter_data_tool,
    calculate_statistics_tool,
    generate_visualization_tool
])
```

### 3. Content Generation Systems
Create systems that can generate various types of content.

```python
# Content generation agent
content_agent = factory.create_agent(tools=[
    generate_outline_tool,
    write_paragraph_tool,
    create_summary_tool,
    check_grammar_tool
])
```

### 4. Multi-Step Workflows
Build complex workflows that involve multiple steps and agent coordination.

```python
# Multi-step workflow using orchestration
orchestrator.submit_task(
    "Analyze our customer feedback emails, identify common issues, " +
    "and generate a summary report with recommendations"
)
```

### 5. Custom APIs
Expose agent capabilities through APIs for integration with other systems.

```python
# Example of exposing agent capabilities as an API endpoint
@app.route('/analyze', methods=['POST'])
def analyze_endpoint():
    data = request.json
    result = analysis_agent.run(data['query'])
    return jsonify({'result': result})
```

## Best Practices

### Tool Design

1. **Single Responsibility**: Each tool should do one thing well.
   ```python
   @tool
   def count_words(text: str) -> int:
       """Count the number of words in a text."""
       return len(text.split())
   ```

2. **Clear Documentation**: Provide clear descriptions and parameter documentation.
   ```python
   @tool
   def format_json(data: dict) -> str:
       """
       Format a dictionary as a JSON string with indentation.
       
       Args:
           data: The dictionary to format
           
       Returns:
           Formatted JSON string
       """
       return json.dumps(data, indent=2)
   ```

3. **Input Validation**: Validate inputs to ensure robustness.
   ```python
   @tool
   def calculate_percentage(value: float, total: float) -> float:
       """Calculate percentage of a value relative to a total."""
       if total == 0:
           raise ValueError("Total cannot be zero")
       return (value / total) * 100
   ```

### Agent Creation

1. **Always use the factory pattern**: Don't create tools directly.
   ```python
   # Correct
   factory = AgentFactory.get_instance()
   factory.create_tool(name="tool_name", ...)
   
   # Incorrect
   tool = Tool(name="tool_name", ...)
   ```

2. **Choose the right agent pattern** for your use case:
   - Basic Agent: For simple, focused agents
   - Factory Agent: When managing multiple tools
   - Decorator Agent: For clean, maintainable code
   - Dynamic Agent: For adaptive, task-specific agents
   - Orchestration: For complex workflows

3. **Register tools explicitly** when using decorators:
   ```python
   @tool
   def my_tool(): ...
   
   factory.register_tool(my_tool._tool)
   ```

### Performance and Scaling

1. **Use rate limiting** to control resource usage:
   ```python
   @tool(rate_limit=10)
   def expensive_operation(): ...
   ```

2. **Monitor tool usage** to identify bottlenecks:
   ```python
   status = factory.get_status()
   for tool_name, stats in status["tools"].items():
       print(f"{tool_name}: {stats['calls']}/{stats['limit']} calls")
   ```

3. **Consider external tools** for computationally intensive operations:
   - Implement in C, Rust, or Go for performance
   - Use the external tool integration

By following these examples and best practices, you can create powerful AI agents that solve complex problems using the tinyAgent framework.
