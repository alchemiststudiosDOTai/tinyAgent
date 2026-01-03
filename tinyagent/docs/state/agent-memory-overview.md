---
title: AgentMemory (Scratchpad)
path: memory/scratchpad.py
type: file
depth: 1
description: Working memory scratchpad for agent variables and observations
seams: [store(), recall(), observe(), fail(), clear(), to_context(), to_namespace()]
---

# AgentMemory (Scratchpad)

## Overview

`AgentMemory` is the working memory scratchpad for agents to maintain state across reasoning steps within a single execution cycle. It provides simple key-value storage for computed values, observations, and tracking failed approaches.

## Implementation

```python
@dataclass
class AgentMemory:
    variables: dict[str, Any] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)
    failed_approaches: list[str] = field(default_factory=list)
```

### State Components

1. **variables**: Dictionary for arbitrary computed values
2. **observations**: List recording learned information
3. **failed_approaches**: List tracking unsuccessful strategies

## API Methods

### store(name: str, value: Any) -> None
Save a variable to memory.

```python
memory.store("api_key_valid", True)
memory.store("user_id", 12345)
```

### recall(name: str, default: Any = None) -> Any
Retrieve a variable from memory.

```python
is_valid = memory.recall("api_key_valid", False)
user_id = memory.recall("user_id")
```

### observe(observation: str) -> None
Record a learning or observation.

```python
memory.observe("The initial API call succeeded.")
memory.observe("User prefers dark mode.")
```

### fail(approach: str) -> None
Record a failed approach to avoid in the future.

```python
memory.fail("Attempted to use old authentication method.")
memory.fail("Direct file access without permission check.")
```

### clear() -> None
Reset all memory state.

```python
memory.clear()  # Clears all variables, observations, and failed approaches
```

### to_context() -> str
Format memory contents into markdown for LLM context.

```python
# Returns formatted string like:
# ## Working Memory
#
# ### Stored Values
# - api_key_valid: True
#
# ### Observations
# - The initial API call succeeded.
#
# ### Failed Approaches (avoid these)
# - Attempted to use old authentication method.
```

### to_namespace() -> dict[str, Any]
Export memory variables for injection into execution namespace.

```python
# Provides dict with memory methods and variables
namespace = memory.to_namespace()
# {
#   "memory": <AgentMemory instance>,
#   "store": <bound method>,
#   "recall": <bound method>,
#   "observe": <bound method>,
#   # Plus all stored variables as top-level keys
# }
```

## Storage Mechanism

- **Type**: In-memory only
- **Data Structures**: Python `dict` and `list`
- **Persistence**: None built-in (state lost on process termination)
- **Thread Safety**: Not thread-safe for concurrent access

## Lifecycle

1. **Creation**: Instantiated at agent initialization
   ```python
   scratchpad = self._initialize_scratchpad()  # In TinyCodeAgent
   ```

2. **Updates**: Methods modify internal structures throughout execution
   ```python
   scratchpad.store("result", compute())
   scratchpad.observe("Computed result successfully")
   ```

3. **Clearing**: Can be reset during execution
   ```python
   scratchpad.clear()  # Reset all state
   ```

## Usage Pattern

```python
# Initialize memory
memory = AgentMemory()

# Store computed values
memory.store("files_checked", 5)
memory.store("all_valid", True)

# Record observations
memory.observe("All files passed validation")

# Track failed attempts
memory.fail("Used incorrect file format")

# Access stored values
if memory.recall("all_valid"):
    print("Validation complete!")

# Export to context for LLM
context = memory.to_context()

# Export to execution namespace
namespace = memory.to_namespace()
exec_globals.update(namespace)
```

## Integration

Used by:
- `TinyCodeAgent` (agents/code.py): Primary user for state management
- Tool execution contexts: Via `to_namespace()` for memory access

## Design Decisions

1. **Simple key-value store**: Chosen for flexibility over typed schema
2. **In-memory only**: Optimized for single-run scenarios
3. **Separate observations list**: Distinguishes between stored values and learned facts
4. **Failed approaches tracking**: Explicit pattern to avoid repeating mistakes

## Considerations

- **No persistence**: Memory lost between runs unless externally serialized
- **No size limits**: Unbounded growth possible (agent must manage)
- **No type safety**: Values can be any type (responsibility of caller)
- **Not thread-safe**: Concurrent access requires external synchronization
