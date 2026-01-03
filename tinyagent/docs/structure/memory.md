---
title: Memory
path: memory/
type: directory
depth: 0
description: Conversation history and agent working state management
seams: [MemoryManager, AgentMemory, Step]
---

## Directory Purpose and Organization

The `memory` directory is a core component of the `tinyagent` project, responsible for managing different aspects of the agent's memory. It's organized into modules that handle distinct memory functionalities:

- **`manager.py`**: Manages a structured conversation history, including adding various "steps" and applying pruning strategies to keep the memory concise
- **`scratchpad.py`**: Provides `AgentMemory`, a less structured, key-value store for an agent's immediate working state (variables, observations, failed approaches)
- **`steps.py`**: Defines the foundational data structures (a hierarchy of `Step` classes) that represent individual units of information in the conversation memory
- **`__init__.py`**: Serves as the package's public interface, exposing key classes and functions to external modules

## Naming Conventions

- **Modules**: Descriptive `snake_case` (e.g., `manager`, `scratchpad`, `steps`)
- **Classes**: `CamelCase` (e.g., `MemoryManager`, `AgentMemory`, `Step`, `ActionStep`)
- **Functions/Methods**: `snake_case` (e.g., `add`, `to_messages`, `keep_last_n_steps`)
- **Type Aliases**: `CamelCase` (e.g., `PruneStrategy`)
- **Internal helper functions**: Within closures use a leading underscore (e.g., `_prune`)
- **`__all__`**: Consistently used in `__init__.py` and module files to explicitly define the public API

## Relationship to Sibling Directories

The `memory` directory provides essential memory services to other parts of the `tinyagent` framework:

- **`agents`**: Consumed by the `agents` directory (e.g., `base.py`, `code.py`, `react.py`) to maintain conversation state, store observations, and track variables across agent turns
- **`execution`**: Would use `MemoryManager` to record actions, tool calls, and their observations
- **`prompts`**: Might interact with `SystemPromptStep` and `TaskStep` to initialize the memory context

This directory forms a foundational layer for the agent's ability to retain context and learn.

## File Structure and Architecture

The `memory` directory exhibits a clear modular and layered architecture:

### Base Data Structures (`steps.py`)

Defines the abstract concept of a `Step` and concrete implementations:

- **`Step`**: The abstract base class for all step types
- **`SystemPromptStep`**: Represents the initial system prompt
- **`TaskStep`**: Represents the user's task or query
- **`ActionStep`**: Represents an action taken by the agent
- **`ScratchpadStep`**: Represents scratchpad state updates

These form the atomic units of memory.

### Structured Conversation Management (`manager.py`)

`MemoryManager` orchestrates these `Step` objects into a chronological conversation history. It provides:

- Methods for adding steps
- Converting steps to LLM-compatible message formats
- Applying flexible `PruneStrategy` functions (e.g., `keep_last_n_steps`, `prune_old_observations`) to manage memory size

### Transient Working Memory (`scratchpad.py`)

`AgentMemory` offers a separate, more immediate "scratchpad" for the agent to:

- Store computed values
- Record observations
- Track failed attempts

The scratchpad can be converted into context strings for the LLM or injected into the execution namespace.

### Public Interface (`__init__.py`)

Consolidates the public-facing elements of these modules, providing a clean API for other parts of the system to interact with.

## Architecture Summary

This separation of concerns allows for distinct memory types (long-term conversation history vs. short-term working state) and promotes maintainability and extensibility of memory management strategies.
