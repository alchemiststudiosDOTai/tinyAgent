---
title: ReactAgent
path: tinyagent/agents/react.py
type: file
depth: 1
description: JSON-based ReAct agent with tool calling adapter support
exports:
  - ReactAgent
seams: [E]
---

# ReactAgent

A JSON-based ReAct (Reasoning + Acting) agent that uses tool-calling adapters to support multiple LLM providers.

## Class Definition

```python
class ReactAgent(BaseAgent):
    """JSON tool-calling agent for general-purpose tasks."""
```

## Initialization Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tools` | `Sequence[Tool]` | `[]` | Available tools for the agent |
| `model` | `str` | `"gpt-4o-mini"` | LLM model identifier |
| `api_key` | `str \| None` | `None` | API key (defaults to env var) |
| `prompt_file` | `str \| None` | `None` | Custom system prompt file path |
| `temperature` | `float` | `0.7` | Sampling temperature |
| `max_tokens` | `int \| None` | `None` | Max tokens per response |
| `tool_calling_mode` | `ToolCallingMode` | `ToolCallingMode.AUTO` | Tool calling strategy |

## Tool Calling Modes

Available via `ToolCallingMode` enum:
- **`AUTO`** - Automatically selects best mode based on model
- **`NATIVE`** - Standard OpenAI-compatible function calling
- **`STRUCTURED`** - OpenAI Structured Outputs with enforced schema
- **`VALIDATED`** - JSON with Pydantic validation
- **`PARSED`** - Lightweight JSON parsing without validation

## Public Methods

### `async run(question: str, max_steps: int = 10, verbose: bool = False, return_result: bool = False)`

Main execution loop for the agent.

**Parameters:**
- `question` - User question/task to solve
- `max_steps` - Maximum reasoning steps (default: 10)
- `verbose` - Enable debug logging
- `return_result` - Return `RunResult` object instead of string

**Returns:** `str | RunResult`

### `run_sync(*args, **kwargs)`

Synchronous wrapper using `asyncio.run()`.

## Response Format

Expects JSON responses with structure:
```json
{
  "scratchpad": "reasoning here",
  "tool": "tool_name",
  "arguments": {"param": "value"}
}
```

Or for final answer:
```json
{
  "scratchpad": "reasoning",
  "answer": "final answer here"
}
```

## Tool Integration

1. **Tool Mapping**: `BaseAgent` builds `_tool_map` for unique names and lookup
2. **Adapter-Based**: Uses `ToolCallingAdapter` for LLM-specific logic
3. **Validation**: Arguments validated against tool signature before execution
4. **Async Support**: Tools executed asynchronously via `_safe_tool`

## Memory System

Uses `tinyagent.core.memory.Memory` class to maintain linear history of:
- System prompts
- User questions
- Assistant responses
- Tool results

## Usage Example

```python
from tinyagent import ReactAgent, tool

@tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"Weather in {city}: Sunny, 72°F"

agent = ReactAgent(
    model="gpt-4o",
    tools=[get_weather],
    tool_calling_mode=ToolCallingMode.NATIVE
)

result = agent.run_sync("What's the weather in Tokyo?")
print(result)
```

## Configuration Notes

- Model selection affects optimal `tool_calling_mode`
- Higher `temperature` increases creativity but may reduce tool accuracy
- Custom prompts can override default ReAct behavior via `prompt_file`
- API key defaults to environment variable (e.g., `OPENAI_API_KEY`)
