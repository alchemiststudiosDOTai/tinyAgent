---
title: MemoryManager
path: memory/manager.py
type: file
depth: 1
description: Manages conversation history as structured Step objects with pruning strategies
seams: [add(), prune(), to_messages(), get_steps_by_type(), clear(), action_count]
---

# MemoryManager

## Overview

`MemoryManager` manages the conversation history as a sequence of structured `Step` objects. It provides methods for adding steps, converting to LLM-compatible messages, and applying pruning strategies to control token usage.

## Implementation

```python
@dataclass
class MemoryManager:
    steps: list[Step] = field(default_factory=list)
```

### Core Components

1. **steps**: Ordered list of `Step` objects representing conversation history
2. **Pruning strategies**: Functions to manage memory growth

## API Methods

### add(step: Step) -> None
Add a new step to the conversation history.

```python
manager.add(SystemPromptStep(content="You are a helpful assistant."))
manager.add(TaskStep(task="Analyze this code."))
manager.add(ActionStep(
    raw_llm_response="I'll analyze the code structure.",
    tool_name="read_file",
    observation="File content loaded."
))
```

**Behavior**:
- Sets `step_number` based on current `len(self.steps)`
- Appends step to end of list

### to_messages() -> list[dict[str, str]]
Convert all steps to LLM-compatible message format.

```python
messages = manager.to_messages()
# Returns:
# [
#   {"role": "system", "content": "You are a helpful assistant."},
#   {"role": "user", "content": "Analyze this code."},
#   {"role": "assistant", "content": "I'll analyze the code structure."},
#   {"role": "user", "content": "Observation: File content loaded."}
# ]
```

**Behavior**:
- Iterates through all steps in order
- Calls `step.to_messages()` for each
- Returns flattened list of message dictionaries

### prune(strategy: PruneStrategy) -> None
Apply pruning strategy to manage memory size.

```python
from tinyagent.memory.manager import keep_last_n_steps, prune_old_observations

# Keep only last 5 action steps (plus system/task)
manager.prune(keep_last_n_steps(5))

# Truncate old observations to 100 chars
manager.prune(prune_old_observations(keep_last_n=3, max_length=100))

# No pruning
manager.prune(no_pruning())
```

**Pruning Strategies**:

1. **keep_last_n_steps(n)**: Keeps last `n` ActionSteps
   - Always preserves SystemPromptStep and TaskStep
   - Removes older ActionSteps entirely

2. **prune_old_observations(keep_last_n, max_length)**: Truncates old observations
   - Keeps last `n` ActionSteps unchanged
   - Truncates observation field in older ActionSteps to `max_length`
   - Preserves SystemPromptStep and TaskStep

3. **no_pruning()**: Identity function, performs no pruning

### get_steps_by_type(step_type: type[T]) -> list[T]
Filter steps by type.

```python
from tinyagent.memory.steps import ActionStep, ScratchpadStep

actions = manager.get_steps_by_type(ActionStep)
notes = manager.get_steps_by_type(ScratchpadStep)
```

### clear() -> None
Remove all steps from history.

```python
manager.clear()  # Resets to empty list
```

### action_count: int
Property returning count of ActionSteps.

```python
num_actions = manager.action_count
```

## Storage Mechanism

- **Type**: In-memory only
- **Data Structure**: Python `list` of `Step` objects
- **Persistence**: None built-in (state lost on process termination)
- **Thread Safety**: Not thread-safe for concurrent access

## Step Types

### SystemPromptStep
Initial system instructions to the LLM.

```python
step = SystemPromptStep(content="You are a code analysis assistant.")
# to_messages() -> [{"role": "system", "content": "..."}]
```

### TaskStep
User's initial query or instruction.

```python
step = TaskStep(task="Analyze the performance of this function.")
# to_messages() -> [{"role": "user", "content": "..."}]
```

### ActionStep
Represents an agent action with tool call and result.

```python
step = ActionStep(
    raw_llm_response="I'll check the file size.",
    tool_name="file_stat",
    tool_args={"path": "/tmp/file.txt"},
    observation="Size: 1024 bytes",
    error=None,
    is_final=False
)
# to_messages() -> [
#   {"role": "assistant", "content": "I'll check the file size."},
#   {"role": "user", "content": "Observation: Size: 1024 bytes"}
# ]
```

**Methods**:
- `truncate(max_length)`: Shorten observation string

### ScratchpadStep
Internal working notes or thoughts.

```python
step = ScratchpadStep(
    content="Need to verify file permissions first",
    raw_llm_response="I should check permissions before reading."
)
# to_messages() -> [
#   {"role": "assistant", "content": "I should check permissions..."},
#   {"role": "user", "content": "Scratchpad noted: Need to verify..."}
# ]
```

## Lifecycle

1. **Creation**: Initialize with empty steps list
   ```python
   manager = MemoryManager()
   # Or via field default
   memory_manager: MemoryManager = field(default_factory=MemoryManager)
   ```

2. **Population**: Add steps throughout execution
   ```python
   manager.add(SystemPromptStep(content="..."))
   manager.add(TaskStep(task="..."))
   manager.add(ActionStep(...))
   ```

3. **Pruning**: Apply strategies to control size
   ```python
   manager.prune(keep_last_n_steps(10))
   ```

4. **Export**: Convert to messages for LLM
   ```python
   messages = manager.to_messages()
   ```

## Usage Pattern

```python
# Initialize
manager = MemoryManager()

# Add initial context
manager.add(SystemPromptStep(content="You are a helpful assistant."))
manager.add(TaskStep(task="Help me analyze this code."))

# Agent loop
for _ in range(max_iterations):
    # Get conversation history
    messages = manager.to_messages()

    # Call LLM
    response = llm.generate(messages)

    # Execute action
    result = execute_tool(response.tool, response.args)

    # Record step
    manager.add(ActionStep(
        raw_llm_response=response.text,
        tool_name=response.tool,
        tool_args=response.args,
        observation=result
    ))

    # Prune if needed
    if len(manager.steps) > threshold:
        manager.prune(keep_last_n_steps(10))
```

## Integration

Used by:
- `TinyCodeAgent` (agents/code.py): Primary user for conversation history
- `ReactAgent` (agents/react.py): Uses simpler `Memory` class, but similar concept

## Design Decisions

1. **Structured Step objects**: Type-safe representation of conversation entries
2. **Pruning strategies**: Separation of memory management logic
3. **to_messages() abstraction**: Encapsulates LLM format conversion
4. **Step numbers**: Sequential indexing for tracking
5. **OpenRouter compatibility**: Uses user messages for observations (not tool messages)

## Considerations

- **No persistence**: History lost between runs unless externally serialized
- **In-memory growth**: Requires pruning for long conversations
- **Not thread-safe**: Concurrent access requires external synchronization
- **Pruning irreversibility**: Pruned steps cannot be recovered
- **Token estimation**: No built-in token counting (relies on strategies)

## Pruning Strategy Examples

```python
# Scenario 1: Long conversation with many actions
# Keep last 10 actions to stay within token limits
manager.prune(keep_last_n_steps(10))

# Scenario 2: Very large observations
# Truncate old observations but keep recent ones intact
manager.prune(prune_old_observations(keep_last_n=3, max_length=200))

# Scenario 3: Testing or debugging
# No pruning to preserve full history
manager.prune(no_pruning())

# Scenario 4: Custom strategy
def custom_strategy(steps: list[Step]) -> list[Step]:
    # Keep system, task, and last 5 actions
    # Remove scratchpad steps older than last 2 actions
    system_tasks = [s for s in steps if isinstance(s, (SystemPromptStep, TaskStep))]
    recent_actions = [s for s in steps if isinstance(s, ActionStep)][-5:]
    return system_tasks + recent_actions

manager.prune(custom_strategy)
```
