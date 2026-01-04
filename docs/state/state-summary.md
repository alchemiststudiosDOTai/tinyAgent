---
title: State Management Summary
path: docs/state/
type: directory
depth: 0
description: Executive summary of state management patterns in tinyAgent
seams: []
---

# State Management Summary

## Overview

tinyAgent employs a multi-layered state management architecture with distinct patterns for different purposes:
- **Working memory**: AgentMemory (scratchpad)
- **Conversation history**: MemoryManager (structured steps)
- **Global state**: Module-level variables and singletons
- **Output limits**: ExecutionLimits (truncation)

## Key Components

### Memory Systems

| Component | Purpose | Lifetime | Thread-Safe |
|-----------|---------|----------|-------------|
| **AgentMemory** | Working memory scratchpad | Per-run | No |
| **MemoryManager** | Conversation history | Per-agent | No |
| **Finalizer** | Final answer state | Per-run | Yes (Lock) |

### Global State

| Component | Type | Scope | Thread-Safe |
|-----------|------|-------|-------------|
| **_PLANS** | Module dict | Global | **No** (concern) |
| **_signal_collector** | Module reference | Global | **No** (concern) |

## State Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Global State                          │
│  ┌────────────────┐  ┌──────────────────────────────┐  │
│  │ _PLANS dict    │  │ _signal_collector reference   │  │
│  │ (NOT thread-safe) │  │ (NOT thread-safe)           │  │
│  └────────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ├─ Used by tools and signals
                          │
┌─────────────────────────────────────────────────────────┐
│                  Per-Agent State                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ TinyCodeAgent / ReactAgent                       │  │
│  │  ┌──────────────┐      ┌──────────────────────┐ │  │
│  │  │ MemoryManager│      │ AgentMemory          │ │  │
│  │  │ (Conversation│      │ (Scratchpad)          │ │  │
│  │  │  History)    │      │  - variables          │ │  │
│  │  │  - steps[]   │      │  - observations       │ │  │
│  │  │  - pruning   │      │  - failed_approaches  │ │  │
│  │  └──────────────┘      └──────────────────────┘ │  │
│  │         │                        │               │  │
│  │         └────────────────────────┘               │  │
│  │                  │                               │  │
│  │           ┌──────▼──────┐                        │  │
│  │           │  Finalizer  │                        │  │
│  │           │ (Thread-safe)│                       │  │
│  │           └─────────────┘                        │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## State Lifecycle

### Initialization
```python
# Agent creation
agent = TinyCodeAgent()
# - MemoryManager: []
# - AgentMemory: {}
# - Finalizer: None
```

### Execution
```python
# During run
agent.memory_manager.add(ActionStep(...))
agent.scratchpad.store("key", value)
agent.finalizer.set(FinalAnswer(...))
```

### Cleanup
```python
# After run
agent.memory_manager.clear()
agent.scratchpad.clear()
agent.finalizer.reset()
```

## Token Management

### Pruning Strategies
- **keep_last_n_steps(n)**: Keep recent actions
- **prune_old_observations(n, max_len)**: Truncate old observations
- **no_pruning()**: Preserve full history

### Output Limits
- **ExecutionLimits.max_output_bytes**: Truncate tool output
- **max_tokens parameter**: Limit LLM response size

### Current Limitations
- No actual token counting
- No token-aware pruning
- Relies on heuristics

## Thread Safety

### Safe Components
- **Finalizer**: Uses `threading.Lock()` for all operations

### Unsafe Components
- **MemoryManager**: No locking (assumes single-threaded)
- **AgentMemory**: No locking (assumes single-threaded)
- **_PLANS**: No locking (global mutable dict - concern)
- **_signal_collector**: No locking (global mutable reference - concern)

### Recommendations
1. Add locking to global state (_PLANS, _signal_collector)
2. Document thread safety assumptions
3. Consider thread-local storage for global state

## Persistence

### Current State
- **No persistence**: All state is in-memory only
- **No serialization**: State lost on process termination
- **No recovery**: Cannot restore from previous runs

### Potential Improvements
```python
# Save conversation history
steps_data = [asdict(step) for step in manager.steps]
save_to_file("history.json", steps_data)

# Save scratchpad
memory_data = {
    "variables": memory.variables,
    "observations": memory.observations
}
save_to_file("memory.json", memory_data)
```

## Caching

### Current State
- **No caching**: No result caching or memoization
- **No token counting**: Delegated to LLM providers
- **Simple design**: Avoids cache invalidation complexity

### Potential Improvements
1. Add token counting with tiktoken
2. Cache expensive tool results
3. Memoize pure functions
4. Implement cache invalidation strategies

## Design Patterns

### Single-Assignment
- **Finalizer**: One final answer per run
- Prevents multiple conflicting answers

### Immutable History
- **Step objects**: Not modified after creation
- Pruning creates new step list

### Working Memory
- **AgentMemory**: Explicit state for reasoning
- Variables, observations, failed approaches

### Structured History
- **Step types**: SystemPrompt, Task, Action, Scratchpad
- Type-safe representation of conversation

## Key Files

| File | Component | Purpose |
|------|-----------|---------|
| `memory/scratchpad.py` | AgentMemory | Working memory |
| `memory/manager.py` | MemoryManager | Conversation history |
| `memory/steps.py` | Step types | History structure |
| `core/finalizer.py` | Finalizer | Final answer |
| `tools/builtin/planning.py` | _PLANS | Plan storage |
| `signals/primitives.py` | _signal_collector | Signal hooks |
| `limits/boundaries.py` | ExecutionLimits | Output truncation |

## Best Practices

### When using AgentMemory
```python
# Store computed values
memory.store("result", compute())

# Record observations
memory.observe("Learned something new")

# Track failures
memory.fail("Avoid this approach")

# Clear between runs
memory.clear()
```

### When using MemoryManager
```python
# Add steps
manager.add(ActionStep(...))

# Prune regularly
if len(manager.steps) > threshold:
    manager.prune(keep_last_n_steps(10))

# Convert to messages
messages = manager.to_messages()
```

### When using global state
```python
# Be cautious with _PLANS (not thread-safe)
# Consider locking for concurrent access

# Set signal collector once
set_signal_collector(my_collector)
```

## Comparison with Other Systems

### vs LangChain
- **LangChain**: More complex state management with memory types
- **tinyAgent**: Simpler, more explicit state control

### vs AutoGPT
- **AutoGPT**: More sophisticated memory with vector storage
- **tinyAgent**: Lightweight in-memory state

### vs BabyAGI
- **BabyAGI**: Task-oriented state management
- **tinyAgent**: Conversation-focused state

## Future Considerations

### Potential Enhancements
1. **Token counting**: Accurate token usage tracking
2. **Persistence**: Save/restore state across runs
3. **Caching**: Memoize expensive operations
4. **Thread safety**: Add locks to global state
5. **Monitoring**: Track state size and growth
6. **Compression**: Reduce memory footprint
7. **Distributed state**: Multi-agent scenarios

### Architectural Decisions
1. **Keep it simple**: Avoid over-engineering
2. **Explicit over implicit**: Clear state management
3. **Fail fast**: Detect state errors early
4. **Document assumptions**: Thread safety, lifecycle

## Conclusion

tinyAgent's state management is **simple, explicit, and effective** for its use cases:
- **Working memory** (AgentMemory) for agent reasoning
- **Conversation history** (MemoryManager) for LLM context
- **Pruning strategies** for token management
- **Output limits** for preventing bloat

The current design prioritizes **simplicity and correctness** over optimization, which is appropriate for the project's goals. Future enhancements should focus on:
1. Token counting for cost management
2. Thread safety for global state
3. Optional persistence for long-running scenarios
4. Selective caching for performance

The architecture is **well-structured** and **extensible**, allowing for incremental improvements as needed.
