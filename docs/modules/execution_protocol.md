---
title: Execution Protocol
path: execution/protocol.py
type: file
depth: 1
description: Standard interface and result structure for code execution backends
exports: [Executor, ExecutionResult]
seams: [M]
---

# execution/protocol.py

## Where
`/Users/tuna/tinyAgent/tinyagent/execution/protocol.py`

## What
Defines interface for code execution backends. Establishes standardized contract that any execution engine must adhere to, enabling consistent interaction with different execution environments.

## How

### Key Classes

**ExecutionResult (dataclass)**
Encapsulates outcomes of code execution:
- `output (str)`: Captured stdout
- `is_final (bool)`: Whether execution produced final answer
- `duration_ms (int)`: Execution time in milliseconds
- `memory_used_bytes (int)`: Memory consumed (if tracked)
- `error (str | None)`: Error message if execution failed
- `timeout (bool)`: Whether terminated due to timeout
- `final_value (Any)`: Final value if is_final is True
- `namespace (dict)`: Execution environment state after running

**Properties:**
- `success` (read-only): True if no error and no timeout

**Executor (Protocol)**
Standard interface for execution backends:
- `run(code: str) -> ExecutionResult`: Execute Python code
- `kill() -> None`: Terminate currently running execution
- `inject(name: str, value: Any) -> None`: Inject variable into namespace
- `reset() -> None`: Clear state, prepare for new execution

**Protocol Features:**
- `@runtime_checkable`: Runtime checking of protocol conformance
- Polymorphic: Different backends implement same interface
- Decoupled: Consumers don't need to know implementation details

## Why

**Design Rationale:**
- **Protocol-Oriented Programming**: Separates interface from implementation
- **Decoupling**: Execution logic isolated from consumers
- **Testability**: Easy to swap mock executors for testing
- **Extensibility**: New backends added without modifying existing code
- **Runtime Checking**: Aids debugging and design validation

**Architectural Role:**
- **Agent Integration**: Agents receive Executor instance for code execution
- **Backend Abstraction**: Local, subprocess, container executors all conform
- **Modularity**: Core logic independent of execution environment
- **Consistency**: Uniform interface across different execution mechanisms

**Dependencies:**
- `typing.Protocol`: Protocol definition
- `dataclasses`: Result structure
- `typing`: Type hints
