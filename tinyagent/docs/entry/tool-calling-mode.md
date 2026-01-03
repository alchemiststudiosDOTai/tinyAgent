---
title: ToolCallingMode
path: tinyagent/core/adapters.py
type: file
depth: 2
description: Enumeration for tool calling adapter modes
exports:
  - ToolCallingMode
  - ToolCallingAdapter
seams: [E]
---

# ToolCallingMode

Enumeration defining different strategies for LLM tool calling interactions.

## Enum Definition

```python
class ToolCallingMode(Enum):
    """Tool calling adapter modes."""
    AUTO = "auto"
    NATIVE = "native"
    STRUCTURED = "structured"
    VALIDATED = "validated"
    PARSED = "parsed"
```

## Mode Details

### AUTO
Automatically selects the best mode based on model capabilities.

**Behavior:**
- Detects model name from initialization
- Chooses optimal mode for detected model
- Prefers STRUCTURED for GPT-4o family
- Falls back to NATIVE for OpenAI-compatible models
- Uses PARSED as final fallback

**Use When:**
- You want automatic optimization
- Testing different models
- Not sure which mode is best
- Default/production usage

**Example:**
```python
agent = ReactAgent(
    model="gpt-4o",
    tool_calling_mode=ToolCallingMode.AUTO  # Uses STRUCTURED
)
```

### NATIVE
Standard OpenAI-compatible function calling.

**Behavior:**
- Uses `tools` parameter in API request
- LLM natively decides when to call tools
- Returns tool calls in `tool_calls` response field
- Most widely supported format

**Use When:**
- Using OpenAI-compatible APIs
- Maximum compatibility needed
- Standard tool calling behavior
- Fine-grained control over tool selection

**Example:**
```python
agent = ReactAgent(
    model="gpt-4o-mini",
    tool_calling_mode=ToolCallingMode.NATIVE
)
```

**Request Format:**
```json
{
  "messages": [...],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "search",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {"type": "string"}
          }
        }
      }
    }
  ]
}
```

### STRUCTURED
OpenAI Structured Outputs with enforced JSON schema.

**Behavior:**
- Forces LLM to adhere to strict JSON schema
- Schema includes tools, scratchpad, and final answer
- Guarantees valid JSON response
- Lower risk of parsing errors

**Use When:**
- Using GPT-4o or GPT-4o-mini
- Need guaranteed response format
- Want to minimize parsing failures
- Can accept schema limitations

**Limitations:**
- Only available on specific OpenAI models
- More restrictive schema than standard JSON
- May impact model creativity

**Example:**
```python
agent = ReactAgent(
    model="gpt-4o",
    tool_calling_mode=ToolCallingMode.STRUCTURED
)
```

**Enforced Schema:**
```json
{
  "type": "object",
  "properties": {
    "scratchpad": {"type": "string"},
    "tool": {"type": "string"},
    "arguments": {"type": "object"},
    "answer": {"type": "string"}
  },
  "additionalProperties": false
}
```

### VALIDATED
JSON parsing with Pydantic validation.

**Behavior:**
- Expects JSON in LLM response text
- Parses JSON from response content
- Validates against Pydantic models
- Ensures type correctness

**Use When:**
- Models don't support native tool calling
- Want strong type validation
- Need detailed validation errors
- Working with non-OpenAI models

**Example:**
```python
agent = ReactAgent(
    model="claude-3-haiku",
    tool_calling_mode=ToolCallingMode.VALIDATED
)
```

**Validation Flow:**
1. Extract JSON from response
2. Parse into Pydantic model
3. Validate types and constraints
4. Raise detailed errors on failure

### PARSED
Lightweight JSON parsing without validation.

**Behavior:**
- Extracts JSON from response text
- Minimal validation (just valid JSON)
- Fastest parsing mode
- Higher risk of type mismatches

**Use When:**
- Performance is critical
- Trust model to output correct types
- Minimal overhead desired
- Fallback from other modes

**Example:**
```python
agent = ReactAgent(
    model="local-model",
    tool_calling_mode=ToolCallingMode.PARSED
)
```

**Risks:**
- No type checking
- No schema validation
- May fail at runtime if types wrong
- Higher debugging burden

## ToolCallingAdapter Protocol

Abstract interface for LLM-specific tool calling logic.

```python
class ToolCallingAdapter(Protocol):
    """Protocol for tool calling adapters."""

    async def format_request(
        self,
        messages: list[dict],
        tools: list[Tool],
        **kwargs
    ) -> dict:
        """Format API request with tools."""
        ...

    def extract_tool_call(
        self,
        response: dict
    ) -> ToolCall | None:
        """Extract tool call from API response."""
        ...

    def validate_tool_call(
        self,
        tool_call: ToolCall,
        tools: dict[str, Tool]
    ) -> None:
        """Validate tool call against available tools."""
        ...
```

## Mode Selection Guide

### By Model

| Model | Recommended Mode | Fallback |
|-------|-----------------|----------|
| GPT-4o | STRUCTURED | NATIVE |
| GPT-4o-mini | STRUCTURED | NATIVE |
| GPT-3.5-turbo | NATIVE | PARSED |
| Claude 3 Opus | VALIDATED | PARSED |
| Claude 3 Haiku | VALIDATED | PARSED |
| Local models | PARSED | - |

### By Use Case

| Use Case | Mode | Reason |
|----------|------|--------|
| Production | AUTO | Automatic optimization |
| Maximum compatibility | NATIVE | Widest support |
| Guaranteed format | STRUCTURED | Enforced schema |
| Custom models | VALIDATED | Strong validation |
| Best performance | PARSED | Minimal overhead |

## Configuration Examples

### Multiple Agents with Different Modes

```python
from tinyagent import ReactAgent, ToolCallingMode

# Production agent with automatic selection
production_agent = ReactAgent(
    model="gpt-4o",
    tool_calling_mode=ToolCallingMode.AUTO
)

# Compatibility-focused agent
compat_agent = ReactAgent(
    model="gpt-3.5-turbo",
    tool_calling_mode=ToolCallingMode.NATIVE
)

# Custom model agent
custom_agent = ReactAgent(
    model="my-custom-model",
    base_url="https://my-api.com",
    tool_calling_mode=ToolCallingMode.VALIDATED
)
```

### Runtime Mode Selection

```python
def create_agent(model_name: str) -> ReactAgent:
    """Create agent with optimal mode for model."""

    if "gpt-4o" in model_name:
        mode = ToolCallingMode.STRUCTURED
    elif "gpt-3.5" in model_name:
        mode = ToolCallingMode.NATIVE
    elif "claude" in model_name:
        mode = ToolCallingMode.VALIDATED
    else:
        mode = ToolCallingMode.PARSED

    return ReactAgent(model=model_name, tool_calling_mode=mode)
```

## Error Handling by Mode

### NATIVE
- Errors from API if tool calling fails
- Clear error messages
- Automatic retries possible

### STRUCTURED
- Schema violations caught early
- Clear validation errors
- Lower failure rate

### VALIDATED
- Pydantic validation errors
- Detailed field-level feedback
- Type mismatch information

### PARSED
- JSON decode errors
- Missing field errors at runtime
- Less detailed error info

## Performance Considerations

| Mode | Overhead | Speed | Reliability |
|------|----------|-------|-------------|
| AUTO | Low | Fast | High |
| NATIVE | Low | Fast | High |
| STRUCTURED | Medium | Medium | Very High |
| VALIDATED | High | Slow | High |
| PARSED | Very Low | Very Fast | Medium |

## Best Practices

1. **Start with AUTO** for automatic optimization
2. **Test modes with your specific model** before production
3. **Use STRUCTURED for GPT-4o** when possible
4. **Fall back to NATIVE** for compatibility
5. **Use VALIDATED for non-OpenAI models**
6. **Consider PARSED for local models** with good prompt engineering
7. **Monitor error rates** and adjust mode accordingly
8. **Profile performance** if speed is critical
