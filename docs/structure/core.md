---
title: Core
path: core/
type: directory
depth: 0
description: Foundational abstractions for LLM interaction, tool management, and agent operations
seams: [ToolCallingAdapter, ToolRegistry, Finalizer, Memory]
---

## Directory Purpose and Organization

The `/core` directory is the foundational layer of the `tinyagent` framework, providing essential utilities, base abstractions, and core logic for building and executing AI agents. Its primary purpose is to define fundamental concepts, data structures, and mechanisms for:

- **LLM Interaction**: Handling different strategies for tool calling and response parsing (`adapters.py`, `parsing.py`)
- **Tool Management**: Defining, registering, and validating tools for agent use (`registry.py`, `schema.py`)
- **Agent Output & State**: Standardizing final answers and overall execution results (`finalizer.py`, `types.py`)
- **Conversational Memory**: Basic storage for agent-LLM interactions (`memory.py`)
- **Error Handling**: Providing specific exceptions for common agent runtime issues (`exceptions.py`)

The directory is organized into distinct modules, each with a focused responsibility, which promotes modularity, maintainability, and extensibility. The `__init__.py` explicitly exposes the public API of the `core` package, making the intended external components clear.

## Naming Conventions

The `/core` directory consistently follows standard Python naming conventions:

- **Modules**: Lowercase with underscores (e.g., `adapters.py`, `parsing.py`)
- **Classes**: PascalCase (e.g., `ToolCallingAdapter`, `Finalizer`, `Tool`, `FinalAnswer`)
- **Functions/Methods**: snake_case (e.g., `get_adapter`, `format_request`, `parse_json_response`, `tool_to_json_schema`). Private helper functions are prefixed with an underscore (e.g., `_safe_json_loads`)
- **Variables/Attributes**: snake_case (e.g., `tool_name`, `steps_taken`, `final_answer`)
- **Constants/Enums**: ALL_CAPS_WITH_UNDERSCORES (e.g., `TOOL_KEY`, `RESPONSE_FORMAT_TYPE`, `AUTO`, `NATIVE`)
- **Type Hinting**: Extensively used throughout for clarity and type safety (e.g., `Sequence[Tool]`, `dict[str, Any]`, `str | None`)

## Relationship to Sibling Directories

The `core` directory forms the central set of abstractions and utilities upon which other top-level `tinyagent` directories build:

- **`agents/`**: Agent implementations (e.g., React, Code agents) rely heavily on `core` for LLM interaction (`adapters`, `parsing`), tool usage (`registry`, `schema`), managing outputs (`finalizer`, `types`), and handling errors (`exceptions`). They use `core.Memory` for conversational context
- **`execution/`**: The execution engine leverages `core.RunResult` to report agent execution outcomes and likely interacts with `core.Finalizer` to capture the final output. It depends on `core.Tool` definitions from the `registry` to invoke actions
- **`memory/` (top-level)**: While `core` provides basic `Memory`, the top-level `memory` directory implements more advanced or persistent memory strategies that integrate with or build upon `core`'s foundational message storage
- **`prompts/`**: This directory contains the specific LLM prompts. These prompts are designed to elicit responses that conform to the structures expected by `core.parsing` and to utilize tools registered via `core.registry` and schematized by `core.schema`
- **`tools/`**: This directory houses the concrete tool implementations. These functions are transformed into callable `core.Tool` objects using the `@tool` decorator from `core.registry`, making them consumable by agents. `core.schema` converts their signatures into JSON Schema for LLM understanding, and `core.adapters` handles argument validation

In essence, `core` provides the glue and fundamental components that enable the specialized functionalities of the other directories to operate within a coherent framework.

## File Structure and Architecture

The architecture of the `core` directory is layered and designed with clear architectural patterns:

### Lowest Layer (Types & Parsing)

- **`types.py`**: Defines immutable data contracts (`FinalAnswer`, `RunResult`) that standardize output
- **`parsing.py`**: Offers stateless utilities for cleaning and extracting structured data from raw LLM text

### Core Logic & Abstractions

- **`finalizer.py`**: Manages the single final answer state using a thread-safe singleton pattern
- **`memory.py`**: Provides a simple, message-based storage mechanism
- **`exceptions.py`**: Centralizes custom error types, used across the framework for consistent reporting

### Tooling Infrastructure

- **`schema.py`**: Acts as the JSON Schema generator, converting Python types and tool signatures into machine-readable formats. This is crucial for LLM understanding
- **`registry.py`**: Implements a registry pattern through the `@tool` decorator, formalizing functions into `Tool` objects with validation and execution capabilities. It leverages `schema.py` to generate tool argument schemas
- **`adapters.py`**: Provides a flexible adapter pattern (`ToolCallingAdapter` protocol) for abstracting LLM-specific tool-calling mechanisms (Native, Structured, Validated, Parsed). It orchestrates schema generation from `registry.Tool` objects via `schema.py` and uses `parsing.py` for response extraction

## Key Architectural Patterns

- **Dependency Inversion Principle (DIP)**: The `ToolCallingAdapter` protocol in `adapters.py` exemplifies DIP, allowing agent logic to depend on an abstraction rather than concrete LLM implementations
- **Registry Pattern**: `registry.py` effectively uses a registry to manage and expose `Tool` objects
- **Singleton Pattern**: `finalizer.py` uses a thread-safe singleton for strict control over the final answer
- **Schema-driven Interaction**: The combination of `schema.py` and `registry.py` drives LLM interaction by providing clear JSON Schemas for tool arguments, enabling robust validation in `adapters.py`
- **Modularity and Separation of Concerns**: Each module has a specific, well-defined role, contributing to a maintainable and understandable codebase

This architectural approach allows `tinyagent` to be highly adaptable to different LLM providers and evolving tool-calling standards while maintaining a clean and robust core.
