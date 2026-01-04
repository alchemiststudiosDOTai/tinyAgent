---
title: Agents
path: agents/
type: directory
depth: 0
description: Agent implementations including BaseAgent, TinyCodeAgent, and ReactAgent
seams: [Tool, ExecutionLimits, MemoryManager, PromptLoader]
---

## Directory Purpose and Organization

The `agents` directory serves as the core module for defining and implementing various types of AI agents within the `tinyagent` framework. It provides a foundational abstract class (`BaseAgent`) that encapsulates common agent functionalities, particularly tool management. This base is extended by specialized agent implementations:

- **TinyCodeAgent**: Agents that execute Python code in a sandboxed environment
- **ReactAgent**: Agents that leverage JSON-based tool calling and the ReAct (Reason + Act) pattern

This structure promotes code reuse, modularity, and a clear distinction between different agent interaction paradigms.

## Naming Conventions

The `agents` directory adheres to standard Python naming conventions:

- **Files**: Descriptive snake_case (e.g., `base.py`, `code.py`, `react.py`)
- **Classes and Enums**: PascalCase (e.g., `BaseAgent`, `TinyCodeAgent`, `ReactAgent`, `TrustLevel`)
- **Methods and Variables**: snake_case (e.g., `_validate_tools`, `run`, `max_steps`)
- **Internal/Protected Members**: Prefix with an underscore (e.g., `_tool_map`, `_executor`)
- **Constants**: ALL_CAPS (e.g., `MAX_STEPS`, `TOOL_KEY`)

## Relationship to Sibling Directories

The `agents` directory acts as a consumer of several other core `tinyagent` modules, integrating their functionalities to build complete agent systems:

- **`core`**: Provides fundamental abstractions and utilities such as `Tool` definitions, `RunResult` types, `Finalizer` for result handling, custom `exceptions` (e.g., `StepLimitReached`), `adapters` for tool calling, and a general `Memory` component (used by `ReactAgent`)
- **`execution`**: `TinyCodeAgent` specifically relies on the `execution` module (e.g., `LocalExecutor`, `ExecutionResult`) to perform sandboxed Python code execution
- **`limits`**: `TinyCodeAgent` uses `ExecutionLimits` from the `limits` module to manage resource constraints during code execution
- **`memory`**: `TinyCodeAgent` integrates with the more detailed memory management system from `memory/manager.py` and `memory/scratchpad.py` for tracking agent steps and state, distinct from the `core.memory` used by `ReactAgent`
- **`prompts`**: Both `TinyCodeAgent` and `ReactAgent` utilize the `prompts` module (e.g., `loader`, `templates`) to retrieve and format their system prompts
- **`signals`**: `TinyCodeAgent` injects LLM communication signals (like `commit`, `explore`, `uncertain`) from the `signals` module into its execution environment

This indicates that `agents` is a higher-level orchestration layer that leverages foundational services from its sibling directories.

## File Structure and Architecture

The architecture within the `agents` directory is characterized by a clear separation of concerns and an adherence to the ReAct pattern:

### `base.py` (`BaseAgent`)
Defines the `BaseAgent` as an abstract base class. It establishes a contract for all agents, primarily by centralizing tool validation, mapping (via `_tool_map`), and ensuring proper tool formatting. This promotes a consistent interface for tool integration across different agent types.

### `code.py` (`TinyCodeAgent`)
Implements a Python-executing ReAct loop:

- Uses a `LocalExecutor` (with placeholders for `SubprocessExecutor` and `DockerExecutor`) for executing generated Python code within defined `ExecutionLimits`
- Employs a sophisticated `MemoryManager` and `AgentMemory` (scratchpad) for detailed tracking of interaction steps, including observations and errors
- Integrates `signals` for structured communication (e.g., `commit` for final answers)
- The agent's main logic resides in the `run` method, which iteratively calls the LLM, extracts code, executes it, and processes results

### `react.py` (`ReactAgent`)
Implements a ReAct loop focused on JSON-based tool calling:

- Leverages `ToolCallingAdapter` from `core.adapters` to handle various LLM tool-calling mechanisms (auto, native, structured, etc.)
- Uses a simpler `Memory` system from `core.memory` to manage conversational history
- The `run` method orchestrates the interaction: calling the LLM, parsing its response for tool calls or final answers, executing tools via `_safe_tool`, and updating memory with observations
- Includes mechanisms for adjusting LLM temperature and attempting a final answer if the step limit is reached without a clear resolution

## Architecture Summary

In summary, the `agents` directory provides a robust and extensible framework for building AI agents, with `BaseAgent` providing a common foundation and `TinyCodeAgent` and `ReactAgent` offering specialized implementations tailored for different interaction styles and computational requirements.
