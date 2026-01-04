---
title: BaseAgent
path: agents/base.py
type: file
depth: 1
description: Abstract base class for all agent types providing common tool management infrastructure
exports: [BaseAgent]
seams: [M]
---

# agents/base.py

## Where
`/Users/tuna/tinyAgent/tinyagent/agents/base.py`

## What
Provides the `BaseAgent` abstract class, which serves as the foundation for all agent implementations within the tinyagent framework. It centralizes common tool management functionality to prevent code duplication across concrete agent types.

## How

### Key Classes

**BaseAgent (ABC)**
- Abstract base class that cannot be instantiated directly
- Takes a `Sequence[Tool]` as constructor argument representing available tools
- Maintains internal `_tool_map` dictionary for efficient tool lookup by name

**Core Methods:**
- `__post_init__`: Initializes agent state by validating tools and building tool map
- `_validate_tools()`: Abstract method for subclasses to implement tool-specific validation
- `_build_tool_map()`: Validates tool types, ensures unique names, populates tool map
- `run(self, *args, **kwargs) -> Any`: Abstract async method - main execution entry point
- `run_sync(self, *args, **kwargs) -> Any`: Synchronous wrapper around `run()`

**Validation Logic:**
- Raises `ValueError` if no tools provided
- Ensures all tools are `Tool` instances
- Enforces unique tool names

## Why

**Design Rationale:**
- Follows DRY principle by abstracting common tool initialization, validation, and mapping logic
- Promotes code reusability and maintainability across different agent types
- Use of `abc.ABC` enforces that concrete agents provide their own `run` method
- Ensures consistent tool handling interface across all agents

**Architectural Role:**
- Sits at top of agent hierarchy in `tinyagent.agents` package
- Provides common interface and shared infrastructure for `ReactAgent` and `TinyCodeAgent`
- Foundational component that defines tool management contract for all agents

**Dependencies:**
- `core.registry.Tool`: Tool definition and validation
- `abc`: Abstract base class functionality
