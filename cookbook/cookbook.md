# tinyAgent Cookbook

This directory contains examples demonstrating different ways to create and use agents within the tinyAgent framework.

## Overview

1. `01_basic_agent.py` - Orchestrator-based agent with complex task management
2. `02_factory_agent.py` - Direct agent creation with factory pattern
3. `03_decorator_agent.py` - Simplified agent creation using decorators
4. `04_dynamic_agent.py` - Dynamic agent creation based on task requirements
5. `05_mcp_orchestration.py` - Complex orchestration with MCP integration
6. `05_elder_brain_mcp_orchestration.py` - ElderBrain architecture with direct control
7. `05_elder_brain_report_generation.py` - ElderBrain content generation capabilities
8. `05_file_manipulator.py` - Agent with file CRUD operations
9. `06_text_browser.py` - Advanced web content extraction with custom text browser

## Running the Examples

Make sure you have set up your environment variables correctly before running these examples. At minimum, you'll need:

```
OPENROUTER_API_KEY=your_api_key_here
```

For examples using MCP (Model Context Protocol) like `05_mcp_orchestration.py`, you may also want to set:

```
BRAVE=your_brave_api_key_here
```

### Running an Example

```bash
cd /path/to/tinyagentV0.3
python examples/01_basic_agent.py
```

## Example Details

### 1. Basic Agent (Orchestrator Pattern)

A sophisticated implementation using the Orchestrator pattern for complex task management. Shows:
- Multi-layer task processing (Orchestrator → Triage → ElderBrain → Agent)
- Built-in task tracking and management
- Permission handling system
- Detailed logging and monitoring
- Dynamic tool loading

**Best for:**
- Enterprise applications requiring multiple agents
- Complex systems needing coordination
- Applications requiring detailed logging and monitoring
- Systems needing permission management
- Large-scale deployments

### 2. Factory Agent (Direct Pattern)

A streamlined implementation using the factory pattern for direct agent creation. Features:
- Direct tool registration and management
- Rate limiting capabilities
- Tool usage statistics
- Simplified execution flow
- Minimal overhead

**Best for:**
- Simple applications
- Quick prototyping
- Learning/understanding basic agent concepts
- Single-agent systems
- Performance-critical applications

### 3. Decorator Agent

Shows a more concise way to define tools using decorators. Highlights:
- Type hint integration for automatic parameter mapping
- Simplified tool creation syntax
- Optional parameters

### 4. Dynamic Agent

Showcases dynamic agent creation based on natural language requirements. Demonstrates:
- Task analysis to determine required tools
- Automatic tool selection
- Dynamic agent specialization

#### How It Works

The Dynamic Agent system uses a sophisticated factory pattern to create specialized agents based on task requirements. Here's the step-by-step process:

1. **Tool Registration**
```python
# Create the dynamic agent factory
factory = DynamicAgentFactory.get_instance()

# Register tools using decorators
@tool
def count_words(text: str) -> int:
    """Count the number of words in a text."""
    return len(text.split())

# Or register directly with factory
factory.create_tool(
    name="multiply",
    description="Multiply two numbers",
    func=lambda a, b: a * b
)
```

2. **Dynamic Agent Creation**
```python
# Create specialized agents based on task
text_agent = factory.create_dynamic_agent(
    "I need to analyze and transform some text data"
)
math_agent = factory.create_dynamic_agent(
    "I need to perform some mathematical calculations"
)
```

3. **Tool Selection Process**
- The system analyzes the task description
- Identifies required capabilities
- Selects appropriate tools
- Creates a specialized agent with only the needed tools

4. **Task Execution**
```python
# Create a demo agent with specific tools
demo_factory = AgentFactory.get_instance()
demo_factory.create_tool(name="count_words", ...)
demo_factory.create_tool(name="multiply", ...)
demo_agent = Agent(factory=demo_factory)

# Execute a task
result = demo_agent.run(
    "Count the words in 'The quick brown fox' and multiply by 2"
)
```

#### Key Features

1. **Dynamic Tool Selection**
- Agents automatically select appropriate tools based on task requirements
- Tools can be combined for complex operations
- New tools can be added at runtime

2. **Tool Creation Methods**
- Decorator-based tool creation
- Direct factory registration
- Dynamic runtime tool creation
- External tool integration

3. **Task-Specific Specialization**
- Each agent is optimized for its specific task
- Reduces overhead by only loading required tools
- Improves performance and resource usage

#### Example Flow

1. **Initial Setup**
```python
# Register tools for different purposes
register_text_tools(factory)
register_math_tools(factory)
register_utility_tools(factory)
```

2. **Agent Creation**
```python
# Create specialized agents
text_agent = factory.create_dynamic_agent(text_task)
math_agent = factory.create_dynamic_agent(math_task)
mixed_agent = factory.create_dynamic_agent(mixed_task)
```

3. **Task Execution**
```python
# Execute a specific task
execution_task = "Count the words in 'The quick brown fox' and multiply by 2"
result = demo_agent.run(execution_task)
```

#### Best Practices

1. **Tool Organization**
- Group related tools together
- Use clear, descriptive tool names
- Provide detailed tool descriptions
- Include type hints for parameters

2. **Agent Creation**
- Use the factory pattern for agent creation
- Create specialized agents for specific tasks
- Monitor tool selection and usage
- Implement proper error handling

3. **Performance Optimization**
- Only register necessary tools
- Use appropriate tool combinations
- Monitor execution times
- Implement caching where appropriate

#### Use Cases

1. **Text Processing**
- Document analysis
- Content transformation
- Data extraction
- Text statistics

2. **Mathematical Operations**
- Calculations
- Data analysis
- Statistical processing
- Numerical transformations

3. **Mixed Operations**
- Combined text and math operations
- Data processing pipelines
- Complex transformations
- Multi-step operations

### 5. File Manipulator

The file manipulation example demonstrates how to create a tool that provides safe CRUD operations on files within a configured directory.

#### Features
- Create new files
- Read file contents
- Update existing files
- Delete files
- List directory contents
- Safe path handling
- Error handling

#### Usage
```python
# Create a file
agent.run("Create a file named 'test.txt' with content 'Hello, World!'")

# Read a file
agent.run("Read the contents of 'test.txt'")

# Update a file
agent.run("Update 'test.txt' with content 'Hello, tinyAgent!'")

# List directory
agent.run("List all files in the output directory")

# Delete a file
agent.run("Delete the file 'test.txt'")
```

#### Safety Features
- Path validation and sanitization
- Directory confinement
- File existence checks
- Error handling and reporting

#### Output Directory
All file operations are performed within a `tinyAgent_output` directory that is automatically created if it doesn't exist.

#### Running the Example
```bash
python cookbook/05_file_manipulator.py
```

### 6. Text Browser Tool

The text browser tool provides advanced web content extraction capabilities with features like:
- Connection pooling with retry logic
- Randomized headers with user agent rotation
- Optional random delays to mimic human browsing
- Parallel URL fetching
- Proxy support
- Viewport-based content navigation

#### Features
- Web page content extraction
- Link extraction
- Search functionality
- Viewport-based navigation
- Parallel URL fetching
- Proxy support
- User agent rotation
- Random delays

#### Usage
```python
# Direct function usage
result = custom_text_browser_function(
    url='https://example.com',
    action='visit',
    use_proxy=False,
    random_delay=True
)

# Access the content
content = result.get('content', '')
title = result.get('title', 'No title')
viewport_info = result.get('viewport_info', {})

# Print results
print(f"Title: {title}")
print(f"Content: {content[:500]}...")  # First 500 chars
print(f"Viewport: Page {viewport_info.get('current', 1)} of {viewport_info.get('total', 1)}")
```

#### Available Actions
- `visit` - Visit a webpage and extract content
- `search` - Search for text within a page
- `links` - Extract all links from a page
- `next_page` - Navigate to next viewport
- `prev_page` - Navigate to previous viewport
- `state` - Get current browser state
- `fetch_parallel` - Fetch multiple URLs in parallel

#### Configuration Options
- `use_proxy` - Enable/disable proxy support
- `random_delay` - Add random delays between requests
- `max_retries` - Maximum number of retry attempts
- `timeout` - Request timeout in seconds

#### Running the Example
```bash
python cookbook/06_text_browser.py
```

#### Best Practices
- Use random delays to avoid rate limiting
- Enable proxy support for production use
- Handle viewport navigation for long content
- Implement proper error handling
- Use parallel fetching for multiple URLs

## Working with External Tools

tinyAgent supports external tools implemented in other languages via a JSON-based communication protocol. External tools are loaded from the `external_tools` directory, where each tool has its own subdirectory containing:

- A `manifest.json` file defining the tool's name, description, parameters, and executable
- The executable file itself (can be in any language - C, Go, Rust, Bash, etc.)

Example external tools:
- `text_rank` - Text compression using the TextRank algorithm (implemented in C)

External tools are automatically loaded when tinyAgent starts and can be used like any other tool through:
- Direct execution via the CLI: `python main.py text_rank "text to compress"`
- Within Agent instances via the factory

## Best Practices

- Use the Orchestrator pattern (`01_basic_agent.py`) for complex systems requiring multiple agents and coordination
- Use the Factory pattern (`02_factory_agent.py`) for simple applications or when performance is critical
- **Always** create Agent instances using a factory rather than passing tools directly
- When building a system with multiple agents, use the Factory and Orchestrator
- For dynamic requirements, use the DynamicAgentFactory
- When integrating with external APIs or services, leverage the MCP capabilities
- For computationally intensive operations, consider implementing external tools in languages like C/C++, Rust, or Go
