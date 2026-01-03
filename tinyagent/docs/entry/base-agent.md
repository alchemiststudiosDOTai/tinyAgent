---
title: BaseAgent
path: tinyagent/agents/base.py
type: file
depth: 1
description: Abstract base class providing shared tool mapping and validation
exports:
  - BaseAgent
seams: [E]
---

# BaseAgent

Abstract base class that provides shared tool mapping and validation logic for all agent implementations.

## Class Definition

```python
class BaseAgent(ABC):
    """Abstract base for all agent types."""
```

## Purpose

Provides common functionality for:
- Tool registration and validation
- Tool name mapping for unique identification
- Shared execution patterns

## Initialization

```python
def __init__(self, tools: Sequence[Tool] = ()):
    """
    Initialize base agent with tools.

    Args:
        tools: Sequence of Tool objects to register

    Raises:
        ValueError: If tool names are not unique
    """
```

## Tool Mapping

The `_tool_map` attribute provides:
- **Unique naming**: Ensures no duplicate tool names
- **Fast lookup**: Dictionary-based tool retrieval
- **Validation**: Checks for conflicts at initialization

```python
# Internal tool map structure
self._tool_map: dict[str, Tool] = {
    tool.name: tool for tool in tools
}
```

## Abstract Methods

### `async run(*args, **kwargs)`

Must be implemented by subclasses.

**Purpose:** Define the main execution loop for the specific agent type.

**Implemented by:**
- `ReactAgent.run(question, max_steps, verbose, return_result)`
- `TinyCodeAgent.run(task, max_steps, verbose, return_result)`

### `run_sync(*args, **kwargs)`

Synchronous wrapper provided by base class.

```python
def run_sync(self, *args, **kwargs):
    """Synchronous wrapper using asyncio.run()."""
    return asyncio.run(self.run(*args, **kwargs))
```

## Protected Methods

### `_validate_tools(tools: Sequence[Tool])`

Validates tool collection before registration.

**Checks:**
- All items are `Tool` instances
- Tool names are unique
- Tools have required metadata

**Raises:**
- `ValueError`: If validation fails

## Tool Registration Flow

```python
# 1. Tools provided to agent
tools = [search_tool, calculator_tool]

# 2. BaseAgent validates
self._validate_tools(tools)

# 3. Tool map created
self._tool_map = {
    "search": search_tool,
    "calculator": calculator_tool
}

# 4. Subclasses use _tool_map for execution
```

## Usage by Subclasses

### ReactAgent
```python
class ReactAgent(BaseAgent):
    def __init__(self, tools=(), **kwargs):
        super().__init__(tools)  # Build tool map
        # ... React-specific setup

    async def _safe_tool(self, tool_name: str, arguments: dict):
        tool = self._tool_map[tool_name]  # Lookup tool
        return await tool.run(arguments)
```

### TinyCodeAgent
```python
class TinyCodeAgent(BaseAgent):
    def __init__(self, tools=(), **kwargs):
        super().__init__(tools)  # Build tool map
        # ... Code-specific setup

    def _inject_tools(self, executor):
        for name, tool in self._tool_map.items():
            executor.inject(name, tool.fn)  # Inject into namespace
```

## Extension Points

When creating custom agents:

1. **Inherit from BaseAgent**
2. **Call `super().__init__(tools)`** to build tool map
3. **Implement `async run()`** with your execution logic
4. **Use `self._tool_map`** for tool lookups

```python
class MyCustomAgent(BaseAgent):
    def __init__(self, tools=(), **kwargs):
        super().__init__(tools)
        # Custom initialization

    async def run(self, input_data, max_steps=10):
        # Custom execution loop
        tool = self._tool_map["my_tool"]
        result = await tool.run(args)
        return result
```

## Design Principles

### Single Responsibility
- BaseAgent handles tool management only
- Subclasses handle execution logic

### Open/Closed
- Open for extension via inheritance
- Closed for modification of core tool logic

### Dependency Inversion
- Depends on `Tool` abstraction
- Not tied to specific tool implementations

## Validation Rules

### Tool Name Uniqueness
```python
# This will raise ValueError
tools = [
    Tool("search", fn=search1),
    Tool("search", fn=search2)  # Duplicate name
]
agent = ReactAgent(tools=tools)
```

### Tool Type Checking
```python
# Only Tool instances allowed
tools = ["not_a_tool"]  # Will fail validation
agent = ReactAgent(tools=tools)
```

## Testing Considerations

When testing agents that inherit from BaseAgent:

1. **Test tool validation** with duplicates
2. **Test tool map lookup** functionality
3. **Test run_sync wrapper** executes async code
4. **Mock tools** for isolated testing

```python
def test_base_agent_validation():
    tool1 = Tool("tool1", fn=lambda: 1)
    tool2 = Tool("tool1", fn=lambda: 2)  # Duplicate

    with pytest.raises(ValueError):
        BaseAgent(tools=[tool1, tool2])
```

## Best Practices

1. **Always call `super().__init__(tools)`** in subclass constructors
2. **Use `self._tool_map`** for all tool lookups (don't maintain separate references)
3. **Validate tools early** (at initialization) to fail fast
4. **Document tool requirements** in subclass docstrings
5. **Handle missing tools gracefully** with clear error messages
