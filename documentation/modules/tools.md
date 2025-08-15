# Tool System Documentation

The tool system in TinyAgent provides a flexible way to register and execute functions that can be called by agents.

## Overview

The tool system consists of:
- A `@tool` decorator for registering functions
- A `Tool` dataclass wrapper for function metadata
- A registry system for tool discovery
- Execution mechanisms for tool calls

## Tool Registration

Tools can be registered using the `@tool` decorator:

```python
from tinyagent import tool

@tool
def calculator(expression: str) -> float:
    """Evaluate a mathematical expression."""
    return eval(expression)
```

The decorator automatically captures:
- Function name
- Docstring for description
- Function signature for argument validation

## Tool Class

The `Tool` class wraps functions with metadata:

### Attributes
- `fn`: The callable function
- `name`: Function name
- `doc`: Function docstring
- `signature`: Function signature from `inspect`

### Methods
- `__call__(*args, **kwargs)`: Direct function call
- `run(payload)`: Execute with dictionary of arguments

## Registry System

The tool registry provides:
- Centralized tool management
- Decorator-based registration
- Immutable views
- Registry freezing for security

### Usage

```python
from tinyagent import tool, get_registry, freeze_registry

@tool
def my_tool(param: str) -> str:
    return f"Processed: {param}"

# Get registry view
registry = get_registry()
tool_obj = registry["my_tool"]

# Freeze registry to prevent changes
freeze_registry()
```

## API Reference

### `@tool` decorator
Register a function as a tool.

### `Tool` class
Wrapper for tool functions.

#### `Tool(fn, name, doc, signature)`
Create a Tool instance.

Parameters:
- `fn`: The callable function
- `name`: Function name
- `doc`: Function docstring
- `signature`: Function signature

#### `run(payload)`
Execute tool with dictionary arguments.

Parameters:
- `payload`: Dictionary of arguments

### Registry Functions

#### `get_registry()`
Return a read-only view of the default registry.

#### `freeze_registry()`
Lock the registry against further changes.

## Security Considerations

- Tools are executed with caller's permissions
- Argument validation prevents signature mismatches
- Registry freezing prevents runtime tool injection
- Tool functions should validate their own inputs
