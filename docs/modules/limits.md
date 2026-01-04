---
title: Execution Limits
path: limits/
type: directory
depth: 1
description: Resource boundary and timeout management for code execution
exports: [ExecutionLimits, ExecutionTimeout]
seams: [M]
---

# limits/

## Where
`/Users/tuna/tinyAgent/tinyagent/limits/`

## What
Defines structure for execution limits and provides mechanisms to enforce time-based limits and manage output size. Ensures agent actions don't run indefinitely or consume excessive resources.

## How

### boundaries.py

**Key Classes:**

**ExecutionTimeout (TimeoutError)**
Custom exception for timeout scenarios:
- Specific error type for timeout handling
- Easy to catch and manage separately from other errors

**ExecutionLimits (dataclass, frozen=True)**
Encapsulates resource constraints:
- `timeout_seconds (int)`: Maximum execution time
- `max_memory_mb (int)`: Memory limit (tracking only, not enforced)
- `max_output_bytes (int)`: Maximum output size
- `max_steps (int)`: Maximum agent steps

**Key Methods:**

**timeout_context() -> Iterator[None]**
Context manager enforcing timeout:
- Unix systems: `signal.SIGALM` for main thread, CPU-bound tasks
- Cross-platform: `threading.Timer` fallback for I/O or other threads
- Usage: `with limits.timeout_context(): ...`

**truncate_output(output: str) -> tuple[str, bool]**
Truncates string if exceeds `max_output_bytes`:
- Returns truncated output and boolean indicating if truncation occurred
- Prevents excessive memory consumption

**Implementation:**
- `_signal_timeout()`: Unix signal-based approach
- `_timer_timeout()`: Threading-based fallback
- `_raise_timeout()`: Common timeout handler

### __init__.py

**Exports:**
- `ExecutionLimits`, `ExecutionTimeout` from boundaries.py

**Purpose:**
- Simplifies imports: `from tinyagent.limits import ExecutionLimits`
- Public interface for limits package

## Why

**Design Rationale:**
- **Dataclass**: Clear, immutable, type-hinted structure
- **Context Manager**: Encapsulates timeout complexity in easy-to-use `with` statement
- **Cross-Platform**: Addresses different OS capabilities with fallback
- **Output Control**: Prevents unbounded output from overwhelming system
- **Sandboxing**: Crucial for stable execution environment

**Architectural Role:**
- **Resource Control**: Prevents indefinite execution and excessive consumption
- **Stability**: Ensures system reliability under load
- **Integration**: Used by `execution` module to wrap code execution
- **Safety**: Fundamental component of execution sandboxing

**Dependencies:**
- `dataclasses`: Immutable limit structure
- `signal`: Unix-based timeout (SIGALRM)
- `threading`: Cross-platform timeout fallback
- `typing`: Context manager and iterator types
