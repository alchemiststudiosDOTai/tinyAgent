---
title: Final Answer Manager
path: core/finalizer.py
type: file
depth: 1
description: Thread-safe singleton for managing agent final answers with idempotent setting
exports: [Finalizer]
seams: [M]
---

# core/finalizer.py

## Where
`/Users/tuna/tinyAgent/tinyagent/core/finalizer.py`

## What
Introduces `Finalizer` class, a thread-safe singleton responsible for managing the "final answer" of an agent's execution. Ensures idempotent final answer setting with immutability after setting.

## How

### Key Class

**Finalizer**
Thread-safe singleton for final answer management:

**Core Methods:**
- `__init__()`: Initializes `_final_answer` to None, creates `threading.Lock`
- `set(value, *, source="normal", metadata=None) -> None`: Attempts to set final answer
  - Raises `MultipleFinalAnswers` if answer already set
  - Accepts value, source ("normal" or "final_attempt"), optional metadata
- `get() -> FinalAnswer | None`: Retrieves set `FinalAnswer` or None
- `is_set() -> bool`: Returns True if final answer set
- `reset() -> None`: Clears current final answer (testing only)

**Thread Safety:**
- Uses `threading.Lock` to protect internal state
- Safe for concurrent access in multi-threaded environments
- Lock ensures atomic check-and-set operation

**Idempotency:**
- First `set()` call succeeds
- Subsequent calls raise `MultipleFinalAnswers` exception
- Once set, answer cannot be changed

## Why

**Design Rationale:**
- **Singleton Pattern**: Single source of truth for final answer
- **Thread Safety**: Prevents race conditions in concurrent execution
- **Idempotency**: Prevents ambiguity from multiple final answers
- **Immutability**: Clear contract for agent output
- **Testability**: `reset()` method for test isolation

**Architectural Role:**
- **Agent Execution**: Agents call `set()` to record conclusions
- **Result Retrieval**: Orchestrators call `get()` to obtain output
- **Standardization**: Ensures single, definitive final answer
- **Consistency**: Prevents conflicting final results

**Dependencies:**
- `core.types.FinalAnswer`: Answer structure
- `core.exceptions.MultipleFinalAnswers`: Error enforcement
- `threading.Lock`: Thread safety
- `typing`: Type hints
