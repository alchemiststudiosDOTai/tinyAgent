---
title: Tool Calling Adapters
path: core/adapters.py
type: file
depth: 1
description: Abstraction layer for LLM tool calling with multi-format support
exports: [ToolCallingAdapter, ToolCallingMode, get_adapter, OpenAIStructuredAdapter, NativeToolAdapter, ValidatedAdapter, ParsedAdapter]
seams: [M]
---

# core/adapters.py

## Where
`/Users/tuna/tinyAgent/tinyagent/core/adapters.py`

## What
Abstracts and manages how tinyagent interacts with various LLMs for tool calling. Provides flexible mechanism to adapt to different LLM capabilities regarding structured output and function calling.

## How

### Key Classes

**ToolCallingMode (Enum)**
Defines tool calling strategies:
- `AUTO`: Automatic detection of model capabilities
- `NATIVE`: Native OpenAI-compatible function calling
- `STRUCTURED`: Structured output format (JSON schema)
- `VALIDATED`: JSON with Pydantic validation
- `PARSED`: Basic JSON parsing without validation

**ToolCallingAdapter (Protocol)**
Core interface all adapter implementations must follow:
- `format_request`: Prepare tool definitions and messages for specific LLM API
- `extract_tool_call`: Parse LLM response to identify tool invocations
- `validate_tool_call`: Ensure arguments match tool schema
- `format_assistant_message`: Convert LLM response to consistent format
- `format_tool_result`: Format tool execution results for memory

**Adapter Implementations:**
- `OpenAIStructuredAdapter`: For LLMs supporting OpenAI structured output (JSON schema)
- `NativeToolAdapter`: For LLMs with native OpenAI-compatible function calling
- `ValidatedAdapter`: Generic fallback extracting JSON and validating with Pydantic
- `ParsedAdapter`: Basic JSON extraction without validation

**Key Functions:**
- `get_adapter(model, mode)`: Factory function selecting appropriate adapter based on model name and mode
- `_supports_structured_outputs(model)`: Checks model capabilities for structured output
- `_supports_native_tools(model)`: Checks model capabilities for native tools
- `_safe_json_loads(text)`: Safe JSON parsing utility
- `_extract_content(response)`: Extracts content string from various response objects
- `_build_args_model(tool)`: Dynamically creates Pydantic BaseModel from Tool signature

## Why

**Design Rationale:**
- **Adapter Pattern**: Decouples core logic from specific LLM tool calling mechanisms
- **Flexibility**: Easy integration of new LLMs with varying capabilities
- **Extensibility**: New adapters added without major refactoring
- **Maintainability**: LLM API changes isolated to specific adapters
- **Robustness**: Validation prevents invalid arguments from reaching tools

**Architectural Role:**
- Critical intermediary layer between tinyagent and LLMs
- Translates between LLM's "language" for tool calls and tinyagent's internal representation
- Works with `core.registry` for Tool metadata
- Works with `core.schema` for JSON Schema generation

**Dependencies:**
- `core.registry.Tool`: Tool definitions and metadata
- `core.schema`: JSON Schema generation
- `pydantic`: Validation infrastructure
- `openai`: OpenAI API types
