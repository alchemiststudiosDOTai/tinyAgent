---
title: Execution
path: execution/
type: directory
depth: 0
description: Sandboxed code execution with resource limits and safety controls
seams: [Executor, ExecutionLimits, LocalExecutor]
---

## Directory Purpose and Organization

The `execution` directory is a core component responsible for defining and implementing the mechanisms for sandboxed code execution within the `tinyagent` project. It provides an `Executor` protocol (interface) and concrete implementations, notably `LocalExecutor`, for running untrusted or restricted Python code safely.

- **`__init__.py`**: Initializes the `execution` package and exposes the main public interfaces and implementations (`Executor`, `ExecutionResult`, `LocalExecutor`)
- **`protocol.py`**: Defines the abstract contract for code execution via the `Executor` `Protocol` and the `ExecutionResult` dataclass, which encapsulates the outcome of an execution. This separation ensures that different execution backends can adhere to a common interface
- **`local.py`**: Contains `LocalExecutor`, a specific implementation of the `Executor` protocol. This executor uses Python's `exec()` function in a heavily restricted environment, controlling built-ins, imports, and execution resources (like timeouts)

## Naming Conventions

- **Modules/Files**: Use descriptive, lowercase, snake_case names (e.g., `local.py`, `protocol.py`)
- **Classes/Protocols**: Use PascalCase (e.g., `Executor`, `ExecutionResult`, `LocalExecutor`, `FinalResult`)
- **Functions/Methods**: Use lowercase, snake_case (e.g., `run`, `kill`, `inject`). Internal/private methods are prefixed with an underscore (e.g., `_safe_import`, `_final_answer`, `_check_imports`)
- **Variables**: Use lowercase, snake_case (e.g., `allowed_imports`, `start_time`)
- **Constants**: Use SCREAMING_SNAKE_CASE (e.g., `SAFE_BUILTINS`)

## Relationship to Sibling Directories

- **Parent (`tinyagent`)**: `execution` is a subpackage of `tinyagent`, indicating its role as a fundamental service within the larger `tinyagent` framework
- **`limits`**: The `local.py` module imports `ExecutionLimits` and `ExecutionTimeout` from the `../limits` directory. This shows a direct dependency on the `limits` package for managing resource constraints (e.g., execution time, output size) during code execution. This suggests that `limits` provides reusable policies for resource management
- **Other `tinyagent` subpackages (e.g., `agents`, `tools`)**: While not explicitly shown in the provided files, it's highly probable that other parts of `tinyagent`, such as `agents` that might need to run tool code or dynamically generated code, would utilize the `Executor` defined here

## File Structure and Architecture

The `execution` directory exhibits a well-structured and modular architecture:

### Interface/Implementation Separation

The `protocol.py` module clearly defines the `Executor` interface and `ExecutionResult` data structure, separating the "what" (the contract) from the "how" (the implementation).

### Concrete Implementation

`local.py` provides a robust, restricted local execution environment. It includes mechanisms for:

- **Security**: Whitelisting built-ins and imports (`_safe_import`, `_check_imports`)
- **Resource Management**: Integration with `ExecutionLimits` for timeouts
- **Output Handling**: Capturing `stdout`
- **State Management**: Maintaining a controlled namespace and supporting injection of external values
- **Result Reporting**: Using `ExecutionResult` and a `FinalResult` sentinel for clear communication of execution outcomes

### Clear Public API

`__init__.py` explicitly defines the public symbols, guiding consumers on what to import and use.

## Architecture Summary

This design allows for potential future expansion with different executor implementations (e.g., remote executors, containerized executors) without affecting the core logic that consumes the `Executor` protocol.
