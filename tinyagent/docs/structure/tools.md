---
title: Tools
path: tools/
type: directory
depth: 0
description: Built-in tools and validation utilities for agent operations
seams: [ToolRegistry, ToolValidator, BuiltinTools]
---

## Directory Purpose and Organization

The `tools` directory serves as a central hub for defining and organizing various utility functions and external integrations that can be utilized by `tinyagent` agents. It is structured to separate general tool validation from specific built-in tools.

### Organization Structure

- **`tools/`**: The root of the tools package, exporting core validation utilities and all built-in tools
- **`tools/builtin/`**: Subdirectory housing concrete implementations of built-in tools that agents can directly invoke
- **`tools/validation.py`**: Contains logic for validating tool classes to ensure they meet specific structural and safety constraints

## Naming Conventions

- **Directories**: Use lowercase, plural nouns (e.g., `tools`, `builtin`)
- **Modules (Files)**: Use lowercase, singular nouns, often reflecting their primary function (e.g., `planning.py`, `web_browse.py`, `web_search.py`, `validation.py`). `__init__.py` files are standard for Python packages
- **Functions**: Use `snake_case` (e.g., `create_plan`, `web_browse`, `validate_tool_class`). Private helper functions are prefixed with an underscore (e.g., `_get_plan`, `_validate_steps`)
- **Classes**: Use `PascalCase` (e.g., `ToolValidationError`, `_function_analyzer`)
- **Constants**: Use `SCREAMING_SNAKE_CASE` (e.g., `_PLANS`, `_BUILTIN_NAMES`)

## Relationship to Sibling Directories

The `tools` directory is a peer to other top-level directories like `agents`, `core`, `memory`, `execution`, etc.

- **`core`**: The `tools` directory directly leverages the `tinyagent.core.registry.tool` decorator (e.g., in `planning.py`, `web_browse.py`, `web_search.py`) to register functions as tools within the `tinyagent` framework. This indicates a strong dependency on the `core`'s registry system for tool discoverability and execution
- **`agents`**: Agents defined in the `agents` directory import and utilize the tools provided by this `tools` package to perform their tasks

## File Structure and Architecture

### `tools/__init__.py`

Acts as the public interface for the `tools` package:

**Exports**:
- From `builtin` submodule: `create_plan`, `get_plan`, `update_plan`, `web_search`
- From `validation` module: `validate_tool_class`, `ToolValidationError`

This makes it easy for other parts of the `tinyagent` project to import these functionalities directly from `tinyagent.tools`.

### `tools/builtin/__init__.py`

Aggregates and re-exports tools specifically from the `builtin` subpackage:

- Imports from `planning.py`: `create_plan`, `get_plan`, `update_plan`
- Imports from `web_browse.py`: `web_browse`
- Imports from `web_search.py`: `web_search`

### `tools/builtin/planning.py`

Implements in-memory planning tools:

- **Storage**: Uses a simple dictionary `_PLANS` for ephemeral storage
- **Functions**:
  - `create_plan(plan_id: str, steps: list[dict])`: Creates a new plan with validation
  - `get_plan(plan_id: str)`: Retrieves an existing plan
  - `update_plan(plan_id: str, step_index: int, updates: dict)`: Updates a specific step in a plan
- **Integration**: Functions are decorated with `@tool` from `tinyagent.core.registry`, making them discoverable by the agent system
- **Validation**: Includes internal validation (`_validate_steps`) to ensure data integrity for plan steps

### `tools/builtin/web_browse.py`

Provides a web browsing tool:

- **Function**: `web_browse(url: str) -> str`
- **Implementation**:
  - Uses `httpx` for asynchronous HTTP requests
  - Dynamically imports `markdownify` to convert HTML to Markdown (optional dependency)
- **Integration**: Decorated with `@tool` for agent integration

### `tools/builtin/web_search.py`

Offers a web search tool:

- **Function**: `web_search(query: str, count: int = 10) -> str`
- **Implementation**:
  - Leverages the Brave Search API
  - Requires the `BRAVE_SEARCH_API_KEY` environment variable for authentication
  - Uses `httpx` for asynchronous HTTP requests
  - Parses search results and returns a formatted summary
- **Integration**: Decorated with `@tool` for agent integration

### `tools/validation.py`

Contains utilities for statically analyzing and validating tool classes:

- **`validate_tool_class(cls: type) -> None`**: Validates that a tool class meets safety and structural requirements
  - Raises `ToolValidationError` if validation fails

- **`ToolValidationError`**: Exception raised when tool validation fails

**Validation Criteria** (enforced via Python's `ast` module):

- Class-level attributes must be literals
- `__init__` parameter defaults must be literals
- Disallowed constructs:
  - `global` statements
  - `nonlocal` statements
  - `lambda` expressions in methods
  - Undefined names

This module is critical for ensuring the safety, determinism, and serializability of tools, which is vital for an agent framework.

## Architecture Summary

The `tools` directory is well-organized with:

1. **Clear separation of concerns**: Tool implementation is separated from validation
2. **Modular structure**: Built-in tools are organized in their own subdirectory
3. **Safety-first design**: Validation ensures tools are safe, deterministic, and serializable
4. **Clean interface**: Public API is carefully controlled through `__init__.py` files
5. **Extensibility**: New tools can be easily added to the `builtin` directory following established patterns

This architecture provides a robust foundation for agents to interact with external functionalities in a safe and predictable manner.
