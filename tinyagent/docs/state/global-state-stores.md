---
title: Global State Stores
path: .
type: directory
depth: 0
description: Overview of global state management patterns and singleton usage
seams: [Finalizer, _PLANS, _signal_collector, MemoryManager instances, AgentMemory instances]
---

# Global State Stores in tinyAgent

## Overview

tinyAgent uses several global state patterns ranging from true global module-level variables to instance-level state stores. This document catalogs all state management patterns, their thread safety, and lifecycle management.

## State Store Summary

| Component | Type | Scope | Thread-Safe | Persistence |
|-----------|------|-------|-------------|-------------|
| `Finalizer` | Instance-level | Per-run | Yes (Lock) | No |
| `MemoryManager` | Instance-level | Per-agent | No | No |
| `AgentMemory` | Instance-level | Per-run | No | No |
| `_PLANS` | Module-level | Global | No | No |
| `_signal_collector` | Module-level | Global | No | No |

## 1. Finalizer

**Location**: `core/finalizer.py`

**Description**: Manages the final answer of an agent run with single-assignment semantics.

### State Structure
```python
class Finalizer:
    _final_answer: FinalAnswer | None = None
    _lock: threading.Lock
```

### State Lifecycle

1. **Initialization**: `_final_answer` set to `None`
2. **Assignment**: `set()` method assigns value once
3. **Immutability**: Subsequent `set()` calls raise `MultipleFinalAnswers`
4. **Reset**: `reset()` clears state (primarily for testing)

### Thread Safety
- **Mechanism**: Uses `threading.Lock()` for all operations
- **Protected Methods**: `set()`, `get()`, `is_set()`, `reset()`
- **Race Prevention**: Lock prevents concurrent modifications

### Usage Pattern
```python
finalizer = Finalizer()

# In agent execution
if not finalizer.is_set():
    finalizer.set(FinalAnswer(content="Answer", is_final=True))

# Retrieve result
answer = finalizer.get()
```

### Design Considerations
- **Single-assignment**: Ensures only one final answer per run
- **Thread-safe**: Safe for concurrent access
- **Encapsulation**: Prevents direct state mutation

## 2. MemoryManager (Instance State)

**Location**: `memory/manager.py`

**Description**: Manages conversation history for a specific agent instance.

### State Structure
```python
@dataclass
class MemoryManager:
    steps: list[Step] = field(default_factory=list)
```

### State Lifecycle

1. **Creation**: Instantiated via `field(default_factory=MemoryManager)`
2. **Population**: Steps added via `add()` method
3. **Pruning**: Steps modified/removed via `prune()` method
4. **Clearing**: All steps removed via `clear()` method

### Thread Safety
- **Status**: Not thread-safe
- **Assumption**: Typically single-threaded access per agent instance
- **Risk**: Concurrent access to shared instance causes race conditions

### Usage Pattern
```python
# In agent definition
@dataclass
class TinyCodeAgent:
    memory_manager: MemoryManager = field(default_factory=MemoryManager)

# In agent execution
self.memory_manager.add(ActionStep(...))
messages = self.memory_manager.to_messages()
```

### Design Considerations
- **Per-instance state**: Each agent has own memory manager
- **Sequential access**: Designed for single-threaded execution
- **Mutation patterns**: List append/filter/modify operations

## 3. AgentMemory (Instance State)

**Location**: `memory/scratchpad.py`

**Description**: Working memory scratchpad for agent variables and observations.

### State Structure
```python
@dataclass
class AgentMemory:
    variables: dict[str, Any] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)
    failed_approaches: list[str] = field(default_factory=list)
```

### State Lifecycle

1. **Creation**: Instantiated via `_initialize_scratchpad()`
2. **Updates**: State modified via `store()`, `observe()`, `fail()`
3. **Clearing**: All state cleared via `clear()` method

### Thread Safety
- **Status**: Not thread-safe
- **Assumption**: Typically single-threaded access per run
- **Risk**: Concurrent modifications cause data corruption

### Usage Pattern
```python
# In agent initialization
scratchpad = self._initialize_scratchpad()

# During execution
scratchpad.store("key", value)
scratchpad.observe("Learned something")
```

### Design Considerations
- **In-process only**: State lost on process termination
- **No persistence**: Requires external serialization for long-term storage
- **Simple structures**: Uses native Python dict/list

## 4. _PLANS (Global Module State)

**Location**: `tools/builtin/planning.py`

**Description**: Global dictionary storing all plans across agent runs.

### State Structure
```python
_PLANS: dict[str, dict[str, Any]] = {}
```

### State Lifecycle

1. **Initialization**: Empty dict at module load time
2. **Creation**: Plans added via `create_plan(tool_id, plan_id, content)`
3. **Updates**: Plans modified via `update_plan(plan_id, updates)`
4. **Access**: Plans retrieved via `get_plan(plan_id)`
5. **Persistence**: Exists for entire application lifetime

### Thread Safety
- **Status**: NOT thread-safe
- **Risk**: High risk of race conditions in concurrent access
- **Concerns**:
  - Multiple agents writing to same dict
  - Read/write conflicts during updates
  - Partial updates visible to readers

### Usage Pattern
```python
# In tool implementations
from tinyagent.tools.builtin.planning import create_plan, get_plan, update_plan

# Create plan
plan_id = create_plan(tool_id="search", content="Search strategy...")

# Update plan
update_plan(plan_id, {"status": "complete"})

# Retrieve plan
plan = get_plan(plan_id)
```

### Design Considerations
- **True global state**: Shared across all agents/runs
- **No locking**: Concurrent access unsafe
- **UUID-based keys**: Reduces collision risk but doesn't prevent races
- **No cleanup**: Plans persist indefinitely (memory leak risk)

### Recommendations
1. **Add locking**: Wrap operations with `threading.Lock()`
2. **Consider cleanup**: Implement TTL or explicit cleanup mechanism
3. **Alternative**: Move to instance-level state

## 5. _signal_collector (Global Module State)

**Location**: `signals/primitives.py`

**Description**: Global hook for collecting signals emitted by LLM.

### State Structure
```python
_signal_collector: Callable[[Signal], None] | None = None
```

### State Lifecycle

1. **Initialization**: Set to `None` at module load time
2. **Assignment**: Set via `set_signal_collector(collector)`
3. **Usage**: Called by `uncertain()`, `explore()`, `commit()`
4. **Clearing**: Set back to `None` via `set_signal_collector(None)`

### Thread Safety
- **Status**: Not thread-safe
- **Risk**: Moderate - typically set once during setup
- **Concerns**:
  - Concurrent calls to `set_signal_collector()`
  - Reads during assignment

### Usage Pattern
```python
# During setup
from tinyagent.signals.primitives import set_signal_collector

def my_collector(signal: Signal) -> None:
    print(f"Signal: {signal}")

set_signal_collector(my_collector)

# During LLM execution (automatic)
uncertain(uncertainty=0.5)  # Calls collector if set
```

### Design Considerations
- **Global hook**: Single collector for entire application
- **Optional**: Can be `None` (no collection)
- **Setup pattern**: Typically configured once at startup
- **Atomic reads**: Reference reads are atomic in Python

### Recommendations
1. **Add locking**: Protect `set_signal_collector()` with lock
2. **Document usage**: Clarify expected setup/teardown pattern
3. **Consider per-instance**: Alternative instance-level collectors

## Thread Safety Analysis

### Safe Patterns
1. **Finalizer**: Fully thread-safe with explicit locking
2. **Per-instance state**: Safe when not shared across threads

### Unsafe Patterns
1. **Global mutable dict**: `_PLANS` needs locking
2. **Global mutable reference**: `_signal_collector` needs locking
3. **Shared instances**: Concurrent access to MemoryManager/AgentMemory

### Recommendations

1. **Add locking to global state**:
   ```python
   # For _PLANS
   _plans_lock = threading.RLock()

   with _plans_lock:
       _PLANS[plan_id] = plan
   ```

2. **Document thread safety**:
   - Clear documentation of thread-safe vs unsafe components
   - Usage guidelines for concurrent scenarios

3. **Consider thread-local storage**:
   - Move global state to thread-local where appropriate
   - Reduces contention and improves safety

## Lifecycle Management

### Short-lived State (Per-Run)
- `AgentMemory`: Cleared between runs
- `Finalizer`: Reset per execution

### Medium-lived State (Per-Agent)
- `MemoryManager`: Persists for agent lifetime
- Agent instances: Exist during execution

### Long-lived State (Application)
- `_PLANS`: Persists for application lifetime
- `_signal_collector`: Persists for application lifetime

## Persistence

### No Persistence (All State)
All state stores are in-memory only. No built-in serialization or persistence mechanisms.

### Recommendations for Persistence

1. **MemoryManager serialization**:
   ```python
   steps_data = [dataclasses.asdict(step) for step in manager.steps]
   # Save to file/database
   ```

2. **AgentMemory serialization**:
   ```python
   memory_data = {
       "variables": memory.variables,
       "observations": memory.observations,
       "failed_approaches": memory.failed_approaches
   }
   ```

3. **Plan persistence**:
   - Consider file-based storage for `_PLANS`
   - Implement save/load methods

## Best Practices

1. **Prefer instance-level state**: Avoid global state when possible
2. **Document thread safety**: Clearly mark thread-safe vs unsafe components
3. **Use locks for shared state**: Protect concurrent access to global state
4. **Consider lifecycle**: Plan state initialization and cleanup
5. **Test concurrent access**: Verify thread safety claims
