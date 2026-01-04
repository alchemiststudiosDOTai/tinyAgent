---
title: JSON Schema Generation
path: core/schema.py
type: file
depth: 1
description: Python type hints to JSON Schema conversion for tool argument definition
exports: [python_type_to_json_schema, tool_to_json_schema]
seams: [M]
---

# core/schema.py

## Where
`/Users/tuna/tinyAgent/tinyagent/core/schema.py`

## What
Generates JSON Schemas from Python type hints and function signatures, primarily for defining tool arguments within the tinyagent framework. Bridges Python's type system and JSON Schema standard.

## How

### Key Functions

**python_type_to_json_schema(python_type) -> dict[str, Any]**
- Converts Python types to corresponding JSON Schema fragments
- Handles basic types directly (str, int, float, bool)
- Delegates to helper functions for complex types:
  - Lists: `_array_schema`
  - Dicts: `_object_schema`
  - Unions: `_union_schema`
  - Literals: `_literal_schema`
  - Enums: `_enum_schema`

**tool_to_json_schema(tool: Tool) -> dict[str, Any]**
- Generates complete JSON Schema for Tool's expected arguments
- Inspects function signature using `inspect`
- Determines required parameters
- Extracts default values
- Uses `python_type_to_json_schema` for each parameter
- Includes tool documentation as description

**Helper Functions:**
- `_array_schema`: Handles `list[T]` and `Sequence[T]`
- `_object_schema`: Handles `dict[str, T]` and `Mapping[str, T]`
- `_union_schema`: Handles `Union[T1, T2]` and `T1 | T2`
- `_literal_schema`: Handles `Literal["a", "b"]`
- `_enum_schema`: Handles `Enum` types

**Type Support:**
- Primitives: str, int, float, bool
- Collections: list, dict, tuple, set
- Special: Optional, Union, Literal, Enum
- Nested: Complex nested structures

## Why

**Design Rationale:**
- **Automation**: Reduces manual schema definition, less error-prone
- **Robustness**: Ensures tool arguments adhere to predefined types
- **Expressiveness**: Supports advanced Python types for precise definitions
- **Standardization**: Produces JSON Schema compliant with standard

**Architectural Role:**
- Critical for "tool calling" functionality
- Translates Python implementation to structured format for LLMs
- Used by adapters to provide tool descriptions to AI models
- Enables input validation before tool execution

**Dependencies:**
- `core.registry.Tool`: Tool definitions
- `inspect`: Function signature inspection
- `typing`: Type hint handling
- `enum`: Enum type support
