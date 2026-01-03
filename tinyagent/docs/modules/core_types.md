---
title: Core Type Definitions
path: core/types.py
type: file
depth: 1
description: Fundamental data structures for agent answers and execution results
exports: [FinalAnswer, RunResult]
seams: [M]
---

# core/types.py

## Where
`/Users/tuna/tinyAgent/tinyagent/core/types.py`

## What
Defines core data structures for handling final answers and results of agent executions. Provides standardized, immutable containers for agent outputs and execution metadata.

## How

### Key Classes

**FinalAnswer (dataclass, frozen=True)**
Encapsulates final answer produced by agent with metadata:
- `value (Any)`: Actual answer content (any Python type)
- `source (Literal["normal", "final_attempt"])`: How answer was obtained
- `timestamp (float)`: Unix timestamp of creation (defaults to current time)
- `metadata (dict[str, Any])`: Additional custom metadata (defaults to {})

**RunResult (dataclass, frozen=True)**
Complete summary of agent execution:
- `output (str)`: Primary string output from agent
- `final_answer (FinalAnswer | None)`: Structured answer if generated
- `state (Literal["completed", "step_limit_reached", "error"])`: Execution outcome
- `steps_taken (int)`: Total reasoning/execution steps performed
- `duration_seconds (float)`: Total execution time
- `error (Exception | None)`: Exception if terminated with error
- `metadata (dict[str, Any])`: Additional execution metadata

**Design Patterns:**
- `frozen=True`: Ensures immutability after creation
- `__post_init__`: Provides default values for optional fields
- Type hints: All fields explicitly typed for clarity

## Why

**Design Rationale:**
- **Immutability**: Prevents accidental modification, enhances predictability
- **Structure**: Standardized format for passing results and answers
- **Thread Safety**: Immutable dataclasses are thread-safe
- **Clarity**: Explicit fields make self-documenting code

**Architectural Role:**
- **Agent Outputs**: Agents return `FinalAnswer` to signify conclusions
- **Execution Reporting**: `RunResult` wraps entire execution session outcome
- **API/Interface**: Public interface for understanding agent operations
- **Communication**: Standardized data exchange between components

**Dependencies:**
- `dataclasses`: Immutable data structure definitions
- `typing`: Type hints and literals
- `time`: Timestamp generation
