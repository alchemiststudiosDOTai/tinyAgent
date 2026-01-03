---
title: Custom Exceptions
path: core/exceptions.py
type: file
depth: 1
description: Specialized exceptions for agent execution and final answer validation
exports: [StepLimitReached, MultipleFinalAnswers, InvalidFinalAnswer]
seams: [M]
---

# core/exceptions.py

## Where
`/Users/tuna/tinyAgent/tinyagent/core/exceptions.py`

## What
Defines custom exception classes for specific error conditions in agent execution and final answer processing. Provides clear, semantically specific exceptions for robust error handling.

## How

### Key Classes

**StepLimitReached(RuntimeError)**
Raised when agent exceeds maximum steps without final answer:
- `steps_taken (int)`: Number of steps executed
- `final_attempt_made (bool)`: Whether final attempt was made
- `context (dict[str, Any])`: Additional state information

**MultipleFinalAnswers(RuntimeError)**
Raised when attempting to set final answer more than once:
- `first_answer (FinalAnswer)`: Initial final answer
- `attempted_answer (FinalAnswer)`: Answer that triggered exception

**InvalidFinalAnswer(ValueError)**
Raised when proposed final answer fails validation:
- `raw_content (Any)`: Unvalidated content
- `validation_error (Exception | None)`: Underlying exception causing failure

**Exception Hierarchy:**
- All inherit from standard Python exceptions (RuntimeError, ValueError)
- Carry additional context for debugging
- Enable targeted error handling with specific except blocks

## Why

**Design Rationale:**
- **Clarity**: Custom exceptions immediately signal what went wrong
- **Specificity**: Distinct exception types enable targeted error handling
- **Debugging**: Rich context (steps_taken, raw_content) aids diagnosis
- **Robustness**: Explicit error conditions improve system reliability

**Architectural Role:**
- **Agent Execution Loops**: `StepLimitReached` enforces operational bounds
- **Finalizer Component**: `MultipleFinalAnswers` ensures unique final output
- **Validation Logic**: `InvalidFinalAnswer` enforces output integrity
- Fundamental building blocks for error handling throughout framework

**Dependencies:**
- `core.types.FinalAnswer`: Used in MultipleFinalAnswers
- `builtins.RuntimeError`: Base for step limit errors
- `builtins.ValueError`: Base for validation errors
