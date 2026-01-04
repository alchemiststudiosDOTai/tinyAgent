---
title: Limits
path: limits/
type: directory
depth: 0
description: Resource boundaries and timeout management for code execution
seams: [ExecutionLimits, ExecutionTimeout]
---

## Directory Purpose and Organization

The `limits` directory is responsible for defining and managing resource boundaries and timeout mechanisms for code execution within the `tinyagent` project. It is organized into an `__init__.py` for package-level exports and `boundaries.py` for the core logic related to these limits.

## Naming Conventions

- **Modules**: Standard Python snake_case (e.g., `boundaries.py`)
- **Classes**: PascalCase (e.g., `ExecutionLimits`, `ExecutionTimeout`)
- **Attributes/Variables**: snake_case (e.g., `timeout_seconds`, `max_memory_mb`)
- **Methods**: snake_case, with a leading underscore for internal helper methods (e.g., `timeout_context`, `_signal_timeout`)
- **Constants**: Not explicitly present in the provided snippet, but implicit in the default values of `ExecutionLimits`

## Relationship to Sibling Directories

The `limits` directory provides a fundamental service for other parts of the `tinyagent` project that involve running code. Its output, `ExecutionLimits` and `ExecutionTimeout`, is consumed by components in the `execution/` directory (e.g., `local.py` for local code execution), and potentially by `agents/` modules that orchestrate tasks requiring resource control. It acts as a foundational utility layer.

## File Structure and Architecture

### `limits/__init__.py`

Defines the public interface for the `limits` package, exposing:

- `ExecutionLimits`: A dataclass for configuring limits
- `ExecutionTimeout`: A custom exception for when limits are exceeded

### `limits/boundaries.py`

Contains the implementation details for managing execution boundaries:

- **`ExecutionTimeout` (class)**: A custom exception derived from `TimeoutError`, used to signal when a defined execution time limit has been reached. It stores the duration of the timeout

- **`ExecutionLimits` (dataclass)**: Encapsulates various configurable resource limits:
  - `timeout_seconds`
  - `max_memory_mb`
  - `max_output_bytes`
  - `max_steps`

  Methods include:
  - **`timeout_context`**: A context manager that provides a portable way to enforce time limits on blocks of code. It intelligently attempts to use `signal.SIGALRM` for more robust timeout handling on Unix-like systems (within the main thread) and falls back to a `threading.Timer` based approach for cross-platform compatibility
  - **`truncate_output`**: A utility function to ensure that string outputs do not exceed `max_output_bytes`, preventing excessive data consumption or display

### Private Implementation Methods

- **`_signal_timeout`**: Implements the signal-based timeout mechanism for Unix systems
- **`_timer_timeout`**: Implements the threading-based timeout mechanism for cross-platform compatibility

## Architecture Summary

The `limits` directory provides a clean, cross-platform solution for managing resource constraints during code execution, with intelligent fallback mechanisms for different operating systems.
