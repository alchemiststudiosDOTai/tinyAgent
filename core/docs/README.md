# tinyAgent Core Documentation

This directory contains detailed documentation for the tinyAgent core architecture. The documentation is organized into several sections covering different aspects of the framework.

## Table of Contents

1. [Architecture Overview](architecture.md) - High-level overview of the tinyAgent architecture
2. [Tools Framework](tools.md) - Guide to creating and using tools in tinyAgent
3. [External Tools](external_tools.md) - Creating tools in other languages
4. [MCP Integration](mcp.md) - Model Context Protocol integration
5. [Security Configuration](security.md) - Configuring security settings
6. [Future Directions](future_directions.md) - Future possibilities and cross-language capabilities

## Quick Start

```python
from core import Agent, Tool, ParamType
from core.factory.agent_factory import AgentFactory

# Get the singleton factory instance
factory = AgentFactory.get_instance()

# Create a tool with the factory
factory.create_tool(
    name="hello_world",
    description="Say hello to someone",
    func=lambda name: f"Hello, {name}!"
)

# Create an agent with the factory
agent = Agent(factory=factory)

# Run a query
result = agent.run("Say hello to Alice")
print(result)  # Output: "Hello, Alice!"
```

## Configuration

tinyAgent is highly configurable through the `config.yml` file:

```yaml
# Model configuration
model:
  default: "deepseek/deepseek-chat"

# Parsing configuration
parsing:
  strict_json: false
  fallback_parsers:
    template: true
    regex: true

# Code execution security configuration
code_execution:
  allow_dangerous_operations: false
  allowed_operations:
    file_operations: false
    os_operations: false
    imports: ["os", "sys"]

# Rate limiting configuration
rate_limits:
  global_limit: 30  # Default limit for all tools
  tool_limits:      # Tool-specific limits
    web_search: 10
    code_execution: 5

# Dynamic agent configuration
dynamic_agents:
  allow_new_tools_by_default: false
  prioritize_existing_tools: true
  max_agents: 10
```

## Key Components

The tinyAgent core architecture is organized into the following key components:

```
core/
  ├── __init__.py         # Core exports and version
  ├── agent.py            # Agent implementation
  ├── tool.py             # Tool base class
  ├── decorators.py       # Tool decorator
  ├── exceptions.py       # Custom exceptions
  ├── logging.py          # Logging configuration
  ├── chat/               # Chat functionality
  ├── cli/                # Command-line interface
  ├── config/             # Configuration management
  ├── factory/            # Factory pattern implementation
  │   ├── agent_factory.py       # Tool and agent management
  │   ├── dynamic_agent_factory.py # Dynamic agent creation
  │   └── orchestrator.py        # Task orchestration
  ├── mcp/                # Model Context Protocol
  ├── tools/              # Built-in tools
  ├── utils/              # Utility functions
  └── docs/               # Documentation
```

Each component is designed to be modular and well-documented with type hints, making it easy to understand and extend the framework.

## Recent Updates

### Factory-Based Tool Execution

tinyAgent now uses a factory pattern for tool management, providing:

- Centralized tool registration
- Proper usage tracking and statistics
- Consistent rate limiting
- Reliable error handling

All tool executions are processed through the factory to ensure consistent behavior.

### Cross-Language Tool Support

The framework now provides comprehensive support for tools written in languages other than Python:

- Universal JSON interface for cross-language interoperability
- Support for high-performance tools in languages like C, Rust, and Go
- Consistent parameter validation and error handling
- Integration with the factory system for tracking and rate limiting

See [External Tools](external_tools.md) for detailed examples in multiple languages.

## Design Principles

tinyAgent core follows these key design principles:

1. **Modularity**: Components are separated into distinct modules with clear responsibilities
2. **Type Safety**: Comprehensive type hints throughout for better IDE integration and documentation
3. **Error Handling**: Robust error handling with a well-defined exception hierarchy
4. **Documentation**: Detailed docstrings and external documentation
5. **Compatibility**: Backward compatibility with the original tinyAgent API
6. **Extensibility**: Easy to extend with new tools and capabilities
7. **Security with Flexibility**: Default security restrictions with configurable overrides
8. **Polyglot Architecture**: Language-agnostic design enabling cross-language integration

## Contributing

When contributing to tinyAgent core, please follow these guidelines:

1. Add comprehensive type hints to all functions and classes
2. Write detailed docstrings in Google style
3. Add unit tests for new functionality
4. Update documentation as needed
5. Follow PEP 8 style guidelines

## License

tinyAgent is licensed under the Sustainable Business License - see the LICENSE file for details.
