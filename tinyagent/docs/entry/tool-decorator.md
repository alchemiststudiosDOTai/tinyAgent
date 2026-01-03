---
title: tool Decorator
path: tinyagent/core/registry.py
type: file
depth: 2
description: Decorator to create Tool objects with metadata and validation
exports:
  - tool
  - Tool
  - validate_tool_class
seams: [E]
---

# tool Decorator

The `@tool` decorator converts Python functions into `Tool` objects with metadata extraction, validation, and async-aware execution.

## Function Signature

```python
def tool(
    func: Callable | None = None,
    *,
    name: str | None = None,
) -> Tool | Callable[[Callable], Tool]:
    """
    Decorator to create a Tool from a function.

    Args:
        func: Function to decorate (used when called without parens)
        name: Optional custom name (defaults to function name)

    Returns:
        Tool object or decorator function

    Raises:
        ToolDefinitionError: If function lacks type hints
    """
```

## Usage Patterns

### Without Custom Name
```python
@tool
def search(query: str) -> str:
    """Search the web."""
    return f"Results for: {query}"

# Tool name: "search"
```

### With Custom Name
```python
@tool(name="web_search")
def search_func(q: str) -> str:
    """Search the web."""
    return f"Results for: {q}"

# Tool name: "web_search"
```

### Parenthesized Without Name
```python
@tool()
def calculate(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y
```

## Validation Requirements

### Type Hints (Required)
All parameters must have type hints:

```python
# This will raise ToolDefinitionError
@tool
def bad_func(x, y):  # Missing type hints
    return x + y
```

```python
# Correct
@tool
def good_func(x: int, y: int) -> int:
    return x + y
```

### Return Type (Required)
Return type annotation is mandatory:

```python
# This will raise ToolDefinitionError
@tool
def bad_func(x: int) -> None:  # Return type required
    pass
```

### Docstring (Recommended)
Warning issued if docstring is missing:

```python
# Warning: No docstring provided
@tool
def my_func(x: int) -> int:
    return x * 2
```

```python
# Good practice
@tool
def my_func(x: int) -> int:
    """Multiply input by 2."""
    return x * 2
```

## Tool Class

### Attributes
```python
@dataclass(frozen=True)
class Tool:
    name: str              # Function identifier
    fn: Callable           # Original function (sync or async)
    is_async: bool         # Whether function is async
    json_schema: dict      # Auto-generated JSON schema
```

### Methods

#### `async run(self, payload: dict) -> Any`
Execute the tool with arguments.

**Features:**
- Async-aware execution
- Sync tools run in thread pool (non-blocking)
- Validates arguments against function signature
- Returns result or raises exception

```python
result = await my_tool.run({"query": "weather"})
```

#### `json_schema` Property
Auto-generated JSON Schema for LLM prompts:

```python
@tool
def search(query: str, max_results: int = 5) -> list[str]:
    """Search the web and return results."""
    return ["result1", "result2"]

print(search.json_schema)
# {
#     "type": "function",
#     "function": {
#         "name": "search",
#         "description": "Search the web and return results.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "query": {"type": "string"},
#                 "max_results": {"type": "integer", "default": 5}
#             },
#             "required": ["query"]
#         }
#     }
# }
```

## Execution Behavior

### Async Tools
```python
@tool
async def async_fetch(url: str) -> str:
    """Fetch URL asynchronously."""
    import httpx
    async with httpx.AsyncClient() as client:
        return await client.get(url).text

# Runs natively in async context
result = await async_fetch.run({"url": "https://example.com"})
```

### Sync Tools
```python
@tool
def sync_process(data: str) -> str:
    """Process data synchronously."""
    return data.upper()

# Runs in thread pool to avoid blocking
result = await sync_process.run({"data": "hello"})
```

## Integration with Agents

### ReactAgent
```python
from tinyagent import ReactAgent, tool

@tool
def get_weather(city: str) -> str:
    """Get weather for city."""
    return f"Weather in {city}: Sunny"

agent = ReactAgent(tools=[get_weather])
result = agent.run_sync("What's the weather in Paris?")
```

### TinyCodeAgent
```python
from tinyagent import TinyCodeAgent, tool

@tool
def calculate_mean(numbers: list[float]) -> float:
    """Calculate mean of numbers."""
    return sum(numbers) / len(numbers)

agent = TinyCodeAgent(tools=[calculate_mean])
result = agent.run_sync(
    "Use calculate_mean to find the average of [1, 2, 3, 4, 5]"
)
```

## Error Handling

### ToolDefinitionError
Raised during decoration when validation fails:

```python
from tinyagent import ToolDefinitionError

try:
    @tool
    def bad_func(x):  # Missing type hint
        return x
except ToolDefinitionError as e:
    print(f"Tool definition failed: {e}")
```

### Runtime Errors
Raised during `tool.run()` execution:

```python
@tool
def divide(a: float, b: float) -> float:
    """Divide two numbers."""
    return a / b

try:
    result = await divide.run({"a": 1.0, "b": 0.0})
except ZeroDivisionError as e:
    print(f"Tool execution failed: {e}")
```

## Advanced Patterns

### Tools with Complex Types
```python
from typing import Literal

@tool
def format_output(
    data: str,
    style: Literal["json", "xml", "csv"]
) -> str:
    """Format data in specified style."""
    # Implementation
    return formatted_data
```

### Tools with Optional Parameters
```python
from typing import Optional

@tool
def search(
    query: str,
    max_results: int = 10,
    filters: Optional[dict] = None
) -> list[dict]:
    """Search with optional filters."""
    # Implementation
    return results
```

## Best Practices

1. **Always provide type hints** for all parameters and return value
2. **Write clear docstrings** describing behavior and parameters
3. **Use descriptive names** that indicate the tool's purpose
4. **Keep tools simple** and focused on single responsibility
5. **Handle errors gracefully** and return informative messages
6. **Use appropriate types** (str, int, float, bool, list, dict)
7. **Consider async I/O** for network operations or file access

## Testing Tools

```python
import pytest
from tinyagent import tool

@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@pytest.mark.asyncio
async def test_tool_execution():
    result = await add.run({"a": 2, "b": 3})
    assert result == 5

@pytest.mark.asyncio
async def test_tool_validation():
    with pytest.raises(TypeError):
        await add.run({"a": "not_an_int", "b": 3})
```
