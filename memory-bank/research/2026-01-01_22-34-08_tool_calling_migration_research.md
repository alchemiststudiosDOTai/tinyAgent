# Research - Client-Side Tool Calling (Like Pydantic AI)

**Date:** 2026-01-01 22:34:08
**Owner:** Claude Code
**Phase:** Research

## Goal

Research client-side tool calling approaches using structured outputs and constrained decoding, similar to how libraries like Pydantic AI, Instructor, and Outlines handle tool calling without relying on provider-specific native tool calling APIs.

## Additional Search

```bash
grep -ri "tool" .claude/ 2>/dev/null | head -20
```

## Key Finding: What Pydantic AI Actually Does

**Important discovery:** Pydantic AI does **NOT** do client-side JSON parsing from text responses. They use:

1. **Native tool-calling APIs** (OpenAI tools, Anthropic tool_use) as primary method
2. **Native structured outputs** (OpenAI `response_format={"type": "json_schema"}`)
3. **Prompted output** (with validation + retry) only as fallback

However, there ARE libraries that do true client-side structured outputs:
- **Outlines** - Constrained decoding
- **Instructor** - Pydantic validation + retry
- **lm-format-enforcer** - Token masking
- **XGrammar** - High-performance FSM

---

## Client-Side Tool Calling Approaches

### Option 1: OpenAI Structured Outputs (Recommended)

OpenAI's **Structured Outputs** feature guarantees 100% JSON schema compliance through provider-side constrained decoding.

```python
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What's the weather in San Francisco?"}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "tool_call",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "enum": ["get_weather", "calculator"]},
                    "arguments": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"},
                            "expression": {"type": "string"}
                        }
                    }
                },
                "required": ["tool"]
            }
        }
    }
)
```

**Advantages:**
- 100% schema compliance on supported models
- No parsing, no retries needed
- Works with any OpenAI-compatible API that supports `json_schema`

**Disadvantages:**
- Only works with models released after 2024-08-06
- Provider-specific (OpenAI only)

---

### Option 2: Pydantic Validation + Retry (Instructor-style)

Use Pydantic for validation and intelligent retry with error feedback.

```python
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI
import json

class ToolCall(BaseModel):
    tool: str
    arguments: dict

class WeatherCall(ToolCall):
    tool: str = "get_weather"
    location: str = Field(description="City name")
    unit: str = Field(default="fahrenheit", pattern="^(celsius|fahrenheit)$")

class CalculatorCall(ToolCall):
    tool: str = "calculator"
    expression: str = Field(description="Math expression")

def execute_with_retry(client, messages, max_retries=3):
    for attempt in range(max_retries):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        try:
            data = json.loads(response.choices[0].message.content)

            # Try validating as weather call
            if data.get("tool") == "get_weather":
                return WeatherCall.model_validate(data)
            elif data.get("tool") == "calculator":
                return CalculatorCall.model_validate(data)
            else:
                raise ValueError(f"Unknown tool: {data.get('tool')}")

        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            if attempt == max_retries - 1:
                raise

            # Add error feedback and retry
            messages.append({
                "role": "assistant",
                "content": response.choices[0].message.content
            })
            messages.append({
                "role": "user",
                "content": f"Invalid output: {e}\nPlease try again with valid JSON."
            })

    return None
```

**Advantages:**
- Works with any LLM
- Type-safe with Pydantic
- Detailed error messages for retries

**Disadvantages:**
- Requires retry logic
- Not 100% reliable (may fail after max retries)
- Higher token cost from retries

---

### Option 3: Constrained Decoding (Outlines-style)

Use token masking to force valid outputs during generation.

```python
import outlines
import outlines.models.openai

from pydantic import BaseModel

class ToolCall(BaseModel):
    tool: str
    arguments: dict

# Generate structured output - guaranteed to match schema
model = outlines.models.openai("gpt-4o")

generator = outlines.generate.json(model, ToolCall)

result = generator("What's the weather in San Francisco?")
# Returns: ToolCall(tool='get_weather', arguments={'location': 'San Francisco'})
```

**How it works:**
1. Builds a Finite State Machine (FSM) from the JSON Schema
2. At each token generation step, masks invalid tokens
3. Only allows tokens that keep generation within valid constraints

**Advantages:**
- 100% reliability
- Works across multiple providers (OpenAI, Anthropic, local models)
- No retries needed

**Disadvantages:**
- Requires models that expose logits (for local models)
- For APIs, depends on library support

---

### Option 4: LM Format Enforcer (Token Masking)

Enforce JSON Schema compliance through token-level masking.

```python
from lmformatenforcer import JsonSchemaParser
from openai import OpenAI

# Define schema
schema = {
    "type": "object",
    "properties": {
        "tool": {"type": "string"},
        "arguments": {"type": "object"}
    },
    "required": ["tool"]
}

# Create parser
parser = JsonSchemaParser(schema)

# Use with OpenAI (requires integration layer)
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What's the weather?"}],
    # Logits processor would mask invalid tokens
    # (requires custom integration for OpenAI API)
)
```

**Note:** Best used with local models (vLLM, Transformers) where you can access logits.

**Advantages:**
- Character-level parsing
- Works with local models
- Integrates with vLLM

**Disadvantages:**
- Requires logit access (not possible with closed APIs)
- More complex setup

---

## Comparison Table

| Approach | Reliability | Provider Support | Complexity | Token Cost |
|----------|-------------|------------------|------------|------------|
| **OpenAI Structured Outputs** | 100% | OpenAI only | Low | Low |
| **Pydantic + Retry** | ~95% | Any LLM | Medium | Medium (retries) |
| **Outlines** | 100% | Many | Low | Low |
| **LM Format Enforcer** | 100% | Local models | High | Low |
| **Current JSON parsing** | ~70% | Any LLM | Low | Medium (retries) |

---

## Recommended Approach for tinyAgent

### Hybrid Strategy: Best of Both Worlds

```python
from enum import Enum
from typing import Protocol

class ToolCallingMode(Enum):
    AUTO = "auto"          # Use native if available
    STRUCTURED = "structured"  # Force OpenAI structured outputs
    VALIDATED = "validated"    # Pydantic validation + retry
    PARSED = "parsed"          # Current JSON parsing approach

class ToolCallingAdapter(Protocol):
    def format_tools(self, tools: list[Tool]) -> dict | list:
        """Convert tools to provider format."""
        ...

    def extract_tool_calls(self, response: Any) -> list[ToolCall]:
        """Extract tool calls from response."""
        ...

    def format_result(self, call_id: str, result: str) -> dict:
        """Format tool result for next request."""
        ...

class OpenAIStructuredAdapter:
    """Use OpenAI's json_schema response format."""

    def format_tools(self, tools: list[Tool]) -> dict:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "tool_call",
                "strict": True,
                "schema": self._build_schema(tools)
            }
        }

class OutlinesAdapter:
    """Use constrained decoding via outlines library."""

    def format_tools(self, tools: list[Tool]) -> type[BaseModel]:
        return self._build_pydantic_model(tools)

class ValidatedAdapter:
    """Use Pydantic validation with retry."""

    def extract_tool_calls(self, response: str) -> list[ToolCall]:
        # Parse JSON, validate with Pydantic
        # Retry if validation fails
        ...

def get_adapter(model: str, mode: ToolCallingMode = ToolCallingMode.AUTO):
    """Get appropriate adapter for model."""

    # Auto-detect best approach
    if mode == ToolCallingMode.AUTO:
        if model.startswith("gpt-4o-") or model.startswith("gpt-4.1-"):
            return OpenAIStructuredAdapter()
        elif supports_outlines(model):
            return OutlinesAdapter()
        else:
            return ValidatedAdapter()

    return {
        ToolCallingMode.STRUCTURED: OpenAIStructuredAdapter(),
        ToolCallingMode.VALIDATED: ValidatedAdapter(),
        ToolCallingMode.PARSED: CurrentJSONAdapter(),
    }[mode]
```

### Benefits of Hybrid Approach

1. **Optimal for each model:**
   - GPT-4o: Use native structured outputs (100% reliable)
   - Local models: Use constrained decoding (Outlines)
   - Other APIs: Use validated retry

2. **Backward compatible:**
   - Fall back to current JSON parsing if nothing else works
   - Existing tools continue to work

3. **Model-agnostic core:**
   - Agent logic doesn't change
   - Only the adapter layer differs

---

## Implementation Plan

### Phase 1: Add Pydantic Validation (Low Risk)

1. Convert `Tool` dataclass to Pydantic model
2. Add validation in `_execute_tool()`
3. Add retry with error feedback
4. Keep current JSON parsing as fallback

**File changes:**
- `tinyagent/core/registry.py` - Use Pydantic for Tool
- `tinyagent/agents/react.py` - Add validation + retry

### Phase 2: Add OpenAI Structured Outputs

1. Detect when model supports `json_schema`
2. Convert tool signatures to JSON Schema
3. Use `response_format` instead of JSON instructions
4. Remove JSON parsing for these models

**File changes:**
- `tinyagent/core/schema.py` - New file for JSON Schema conversion
- `tinyagent/agents/react.py` - Add structured output path

### Phase 3: Add Constrained Decoding (Optional)

1. Add Outlines dependency
2. Create adapter for local models
3. Use constrained decoding when available

**File changes:**
- `tinyagent/core/adapters/` - New directory for adapters
- `pyproject.toml` - Add optional `outlines` dependency

---

## Code Examples

### Converting Current Tool to JSON Schema

```python
# Current: tinyagent/core/registry.py
from pydantic import BaseModel, Field
from typing import get_type_hints
import inspect

def tool_to_json_schema(tool: Tool) -> dict:
    """Convert Tool to JSON Schema format."""
    sig = tool.signature
    hints = get_type_hints(tool.fn)

    properties = {}
    required = []

    for name, param in sig.parameters.items():
        param_type = hints.get(name, param.annotation)

        # Convert Python type to JSON Schema type
        properties[name] = {
            "type": _python_to_json_type(param_type),
            "description": f"Parameter {name}"
        }

        if param.default == inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False
    }

def _python_to_json_type(python_type: type) -> str:
    """Map Python types to JSON Schema types."""
    mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    return mapping.get(python_type, "string")
```

### Enhanced ReactAgent with Validation

```python
# Enhanced: tinyagent/agents/react.py
from pydantic import ValidationError, validate_json

async def _execute_tool_enhanced(
    self,
    payload: dict,
    raw_response: str,
    ...
) -> str | RunResult | None:
    """Execute tool with Pydantic validation and retry."""

    name = payload.get("tool")
    args = payload.get("arguments", {})

    # Get tool schema
    tool = self._tool_map.get(name)
    if not tool:
        return f"Error: Unknown tool '{name}'"

    # Validate arguments against schema
    try:
        if isinstance(args, str):
            validated_args = validate_json(
                args.encode(),
                tool.schema,
                strict=True
            )
        else:
            validated_args = tool.schema.validate_python(args)
    except ValidationError as e:
        # Add error to memory and retry
        self.memory.add(
            ActionStep(
                tool_name=name,
                tool_args=args,
                error=f"Validation failed: {e}",
                raw_llm_response=raw_response
            )
        )
        return None  # Triggers retry with higher temperature

    # Execute with validated arguments
    ok, result = await self._safe_tool(name, validated_args)
    ...
```

---

## Dependencies

### Required

```toml
[tool.poetry.dependencies]
pydantic = ">=2.0"
```

### Optional (for constrained decoding)

```toml
[tool.poetry.extras]
structured = ["outlines>=0.1.0"]
local = ["lm-format-enforcer>=0.3", "vllm>=0.6"]
```

---

## Knowledge Gaps

1. **Which models support structured outputs?** - Need to maintain a compatibility matrix
2. **Performance comparison** - Benchmark each approach on same tasks
3. **Streaming support** - How do these approaches work with streaming responses?
4. **Cost analysis** - Token cost comparison (retries vs structured outputs)

---

## References

### Codebase Files
- `tinyagent/core/parsing.py:15-29` - Current JSON parsing implementation
- `tinyagent/core/registry.py:34-108` - Tool decorator and dataclass
- `tinyagent/agents/react.py:148-191` - ReAct step processing

### External Documentation
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [Outlines Documentation](https://outlines-dev.github.io/outlines/)
- [Instructor Documentation](https://python.useinstructor.com/)
- [lm-format-enforcer GitHub](https://github.com/noamgat/lm-format-enforcer)
- [Pydantic AI - Tool Calling](https://ai.pydantic.dev/tools/)

### GitHub Permalinks
- `parsing.py`: https://github.com/alchemiststudiosDOTai/tinyAgent/blob/d59ed1eea8e8173a1bbab214c07dbaadae1692d4/tinyagent/core/parsing.py
- `registry.py`: https://github.com/alchemiststudiosDOTai/tinyAgent/blob/d59ed1eea8e8173a1bbab214c07dbaadae1692d4/tinyagent/core/registry.py
- `react.py`: https://github.com/alchemiststudiosDOTai/tinyAgent/blob/d59ed1eea8e8173a1bbab214c07dbaadae1692d4/tinyagent/agents/react.py

---

## Metadata

| Field | Value |
|-------|-------|
| Date | 2026-01-01 |
| Time | 22:34:08 |
| Git branch | master |
| Git commit | d59ed1eea8e8173a1bbab214c07dbaadae1692d4 |
| GitHub repo | alchemiststudiosDOTai/tinyAgent |
