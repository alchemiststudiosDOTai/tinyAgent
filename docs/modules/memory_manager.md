---
title: Memory Manager
path: memory/manager.py
type: file
depth: 1
description: Conversation history management with pruning strategies for LLM context optimization
exports: [MemoryManager, PruneStrategy, keep_last_n_steps, prune_old_observations, no_pruning]
seams: [M]
---

# memory/manager.py

## Where
`/Users/tuna/tinyAgent/tinyagent/memory/manager.py`

## What
Manages conversation history represented as sequence of "steps." Stores steps and provides mechanisms to prune them to manage memory and context length for LLM API calls.

## How

### Key Classes

**MemoryManager**
Central class for memory management:

**Core Attributes:**
- `steps: list[Step]`: Chronological list of conversation steps

**Core Methods:**
- `add(step: Step) -> None`: Append new step with sequential `step_number`
- `to_messages() -> list[dict]`: Convert steps to LLM API message format
- `prune(strategy: PruneStrategy) -> None`: Apply pruning strategy to steps
- `get_steps_by_type(step_type: type[T]) -> list[T]`: Filter steps by class
- `clear() -> None`: Empty the steps list
- `action_count` (property): Return number of ActionStep instances

**PruneStrategy (Type Alias)**
- `Callable[[list[Step]], list[Step]]`: Function modifying steps list
- Promotes functional approach to memory reduction

**Pruning Strategy Functions:**

**keep_last_n_steps(n: int) -> PruneStrategy**
- Keeps last n ActionStep instances
- Always preserves SystemPromptStep and TaskStep objects
- Discards older action-related steps

**prune_old_observations(keep_last_n: int = 3, max_length: int = 100) -> PruneStrategy**
- Truncates ActionStep observations older than last n
- Reduces detail of old observations to max_length
- Preserves System and Task steps

**no_pruning() -> PruneStrategy**
- Identity strategy returning unchanged steps list
- For scenarios where no pruning is desired

## Why

**Design Rationale:**
- **Separation of Concerns**: Manager handles storage, strategies define logic
- **Flexibility**: New pruning strategies easily added without modifying Manager
- **Reusability**: Pruning logic encapsulated in testable functions
- **Maintainability**: Centralized step list management

**Architectural Role:**
- **Short-term Memory**: Agent's working memory for conversation context
- **LLM Integration**: Assembles messages for LLM API calls
- **Context Management**: Applies pruning to stay within token limits
- **Cost Control**: Reduces LLM costs by managing context size

**Dependencies:**
- `memory.steps`: Step type definitions (Step, ActionStep, SystemPromptStep, TaskStep)
- `typing`: Type hints and callables
- `logging`: Warning messages
