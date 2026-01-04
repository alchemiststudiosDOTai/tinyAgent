---
title: Tool Registration and Validation
path: core/registry.py
type: file
depth: 1
description: Tool decorator and wrapper for validated, async-aware function registration
exports: [tool, Tool, ToolDefinitionError]
seams: [M]
---

# core/registry.py

## Where
`/Users/tuna/tinyAgent/tinyagent/core/registry.py`

## What
Defines and manages "Tools" within tinyagent framework. Allows functions to be registered as callable tools with validation rules and async-aware execution handling.

## How

### Key Classes

**Tool (Pydantic model)**
Wraps callable function with metadata:
- `fn (Callable)`: The wrapped function
- `name (str)`: Tool name
- `doc (str)`: Docstring documentation
- `signature (inspect.Signature)`: Function signature
- `is_async (bool)`: Whether function is async

**Key Methods:**
- `__call__()`: Direct calling of wrapped function
- `run()`: Async-aware execution
  - Awaits async functions directly
  - Runs sync functions in thread pool to prevent blocking
- `json_schema` (property): Generates JSON Schema for arguments

**tool (Function Decorator)**
Main entry point for registering functions as Tool objects:
- **Validation Requirements:**
  - All parameters must have type annotations
  - Return type annotation required
  - Warns if missing docstring
  - Determines if function is async
- **Error Handling:**
  - Raises `ToolDefinitionError` if validation fails
  - "Fail-fast" mechanism catches errors at registration

**ToolDefinitionError (Exception)**
Custom exception for tool definition violations

## Why

**Design Rationale:**
- **Type Safety**: Enforces type hints for well-defined interfaces
- **Robustness**: Decorator catches errors at registration, not runtime
- **Async Compatibility**: Abstracts sync/async complexity
- **Self-Documentation**: Encourages docstrings for clarity
- **Schema Generation**: Tools introspectable for LLM integration

**Architectural Role:**
- **Tool Discovery**: Registry for available agent capabilities
- **Action Space**: Defines operations agents can perform
- **Execution Abstraction**: Standardized interface for tool execution
- **Model Integration**: JSON schema for LLM understanding

**Dependencies:**
- `pydantic`: BaseModel validation
- `inspect`: Function signature inspection
- `asyncio`: Thread pool execution
- `core.schema`: JSON schema generation
- `functools.wraps`: Decorator preservation
