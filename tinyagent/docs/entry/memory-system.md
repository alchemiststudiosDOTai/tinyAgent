---
title: Memory System
path: tinyagent/memory/
type: directory
depth: 1
description: Conversation history and working memory management
exports:
  - AgentMemory
  - MemoryManager
  - Step
  - SystemPromptStep
  - TaskStep
  - ActionStep
  - ScratchpadStep
  - PruneStrategy
  - keep_last_n_steps
  - prune_old_observations
  - no_pruning
seams: [E]
---

# Memory System

Comprehensive memory management for conversation history and working state across agent execution.

## Architecture

```
Memory System
├── AgentMemory (Scratchpad)
│   └── Persistent working state across steps
├── MemoryManager
│   └── Structured conversation history with pruning
└── Step Classes
    ├── SystemPromptStep
    ├── TaskStep
    ├── ActionStep
    └── ScratchpadStep
```

## AgentMemory (Scratchpad)

Persistent working memory used by `TinyCodeAgent` to maintain state across code execution steps.

### Class Definition

```python
class AgentMemory:
    """Working memory for persistent state across steps."""

    def store(self, key: str, value: Any) -> None:
        """Store a value in memory."""

    def recall(self, key: str) -> Any:
        """Retrieve a value from memory."""

    def observe(self, observation: str) -> None:
        """Add an observation to the log."""

    def fail(self, error: str) -> None:
        """Record a failure/error."""
```

### Usage Example

```python
from tinyagent import TinyCodeAgent

agent = TinyCodeAgent()

# In agent's generated code:
agent.memory.store("data_format", "CSV")
agent.memory.observe("Found 3 columns in data")

# Later steps can recall:
format = agent.memory.recall("data_format")  # "CSV"
```

### Integration with Execution

```python
# AgentMemory injected into Python execution environment
executor.inject("memory", agent.memory)

# Available in generated code:
memory.store("result", calculation_result)
memory.observe("Calculation completed successfully")
```

### Methods

#### `store(key: str, value: Any) -> None`
Store a value with a key for later retrieval.

**Use Cases:**
- Caching intermediate results
- Remembering data formats
- Storing configuration
- Saving analysis state

#### `recall(key: str) -> Any`
Retrieve a previously stored value.

**Returns:** The stored value or `None` if key not found.

#### `observe(observation: str) -> None`
Log an observation for debugging/analysis.

**Use Cases:**
- Recording discoveries
- Noting patterns
- Debugging information
- Progress tracking

#### `fail(error: str) -> None`
Record a failure or error condition.

**Use Cases:**
- Logging execution errors
- Recording failed approaches
- Error context preservation

## MemoryManager

Manages structured conversation history with step-based organization and optional pruning.

### Class Definition

```python
class MemoryManager:
    """Manage conversation memory with pruning."""

    def __init__(
        self,
        system_prompt: str,
        enable_pruning: bool = False,
        prune_keep_last: int = 3
    ):
        """Initialize memory manager."""

    def add(self, step: Step) -> None:
        """Add a step to memory."""

    def to_messages(self) -> list[dict]:
        """Convert to LLM message format."""

    def prune(self, strategy: PruneStrategy) -> None:
        """Apply pruning strategy."""
```

### Initialization Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `system_prompt` | `str` | Required | System instructions |
| `enable_pruning` | `bool` | `False` | Enable automatic pruning |
| `prune_keep_last` | `int` | `3` | Steps to keep when pruning |

### Usage Example

```python
from tinyagent import MemoryManager, SystemPromptStep, TaskStep

manager = MemoryManager(
    system_prompt="You are a helpful assistant.",
    enable_pruning=True,
    prune_keep_last=5
)

# Add steps
manager.add(SystemPromptStep(content="You are a helpful assistant."))
manager.add(TaskStep(content="What's the weather?"))
manager.add(ActionStep(...))

# Convert to messages
messages = manager.to_messages()
```

### Methods

#### `add(step: Step) -> None`
Add a step to the conversation history.

**Parameters:**
- `step`: Step object (SystemPromptStep, TaskStep, ActionStep, ScratchpadStep)

#### `to_messages() -> list[dict]`
Convert steps to LLM message format.

**Returns:** List of message dictionaries for LLM API.

**Format:**
```python
[
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "Tool result..."}
]
```

#### `prune(strategy: PruneStrategy) -> None`
Apply pruning strategy to reduce memory size.

**Strategies:**
- `keep_last_n_steps(n)` - Keep last N action steps
- `prune_old_observations(max_length)` - Truncate old observations
- `no_pruning` - Identity function (no changes)

## Step Classes

Base class and subclasses for different types of conversation steps.

### Step (Base Class)

```python
@dataclass
class Step:
    """Base class for memory steps."""
    step_type: str
    content: str
    timestamp: datetime
```

### SystemPromptStep

```python
@dataclass
class SystemPromptStep(Step):
    """System prompt/instructions step."""
    step_type: Literal["system"] = "system"
```

**Usage:**
```python
step = SystemPromptStep(content="You are a helpful assistant.")
manager.add(step)
```

### TaskStep

```python
@dataclass
class TaskStep(Step):
    """User task/question step."""
    step_type: Literal["task"] = "task"
```

**Usage:**
```python
step = TaskStep(content="What's the weather in Tokyo?")
manager.add(step)
```

### ActionStep

```python
@dataclass
class ActionStep(Step):
    """Tool call with observation/error step."""
    step_type: Literal["action"] = "action"
    tool_name: str
    arguments: dict
    observation: str | None = None
    error: str | None = None
```

**Usage:**
```python
step = ActionStep(
    content="Calling search tool",
    tool_name="search",
    arguments={"query": "weather Tokyo"},
    observation="Sunny, 72°F"
)
manager.add(step)
```

### ScratchpadStep

```python
@dataclass
class ScratchpadStep(Step):
    """Working memory notes step."""
    step_type: Literal["scratchpad"] = "scratchpad"
```

**Usage:**
```python
step = ScratchpadStep(content="Data format is CSV with 3 columns")
manager.add(step)
```

## Pruning Strategies

Functions to manage memory size by removing old or less relevant steps.

### keep_last_n_steps(n: int)

Keep only the last N action steps.

```python
from tinyagent import keep_last_n_steps

manager.prune(keep_last_n_steps(5))
# Keeps last 5 action steps, removes older ones
```

**Use Case:** Prevent context overflow in long conversations.

### prune_old_observations(max_length: int)

Truncate old observations to specified length.

```python
from tinyagent import prune_old_observations

manager.prune(prune_old_observations(max_length=100))
# Shortens observations longer than 100 characters
```

**Use Case:** Reduce token count while preserving recent detail.

### no_pruning(memory: MemoryManager) -> MemoryManager

Identity function that makes no changes.

```python
from tinyagent import no_pruning

manager.prune(no_pruning)
# Returns manager unchanged
```

**Use Case:** Default behavior or for custom pruning logic.

### Custom Pruning Strategy

Create custom pruning functions:

```python
from tinyagent import MemoryManager, PruneStrategy

def custom_pruner(manager: MemoryManager) -> MemoryManager:
    """Custom pruning logic."""
    # Keep system prompt and task
    # Remove old action steps
    # Keep last 3 action steps
    steps = manager.steps
    new_steps = [
        s for s in steps
        if s.step_type in ["system", "task"]
    ] + steps[-3:]

    manager.steps = new_steps
    return manager

# Use custom strategy
manager.prune(custom_pruner)
```

## Type Alias

```python
PruneStrategy = Callable[[MemoryManager], MemoryManager]
```

Functions that take a `MemoryManager` and return a (possibly modified) `MemoryManager`.

## Integration with Agents

### ReactAgent

```python
from tinyagent import ReactAgent, MemoryManager

memory = MemoryManager(
    system_prompt="You are a helpful assistant.",
    enable_pruning=True
)

agent = ReactAgent(
    memory_manager=memory,
    max_steps=20
)

# Agent adds steps automatically during execution
# Memory pruning happens as configured
```

### TinyCodeAgent

```python
from tinyagent import TinyCodeAgent, AgentMemory

agent = TinyCodeAgent(
    enable_pruning=True,
    prune_keep_last=5
)

# AgentMemory for working state
agent.memory.store("analysis", "in_progress")

# MemoryManager for conversation history
# Automatic pruning based on configuration
```

## Best Practices

1. **Use AgentMemory for working state** in code execution scenarios
2. **Use MemoryManager for conversation history** across all agent types
3. **Enable pruning for long conversations** to prevent context overflow
4. **Choose appropriate prune_keep_last** based on context window
5. **Use appropriate step types** for different kinds of information
6. **Consider token limits** when setting pruning parameters
7. **Test pruning strategies** with your specific use cases
8. **Monitor memory usage** in production

## Performance Considerations

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `add(step)` | O(1) | Simple append |
| `to_messages()` | O(n) | Iterates all steps |
| `prune()` | O(n) | Filters steps |
| Memory usage | O(n) | Linear in steps |

## Debugging

Enable verbose logging to see memory operations:

```python
agent = ReactAgent(
    verbose=True,  # Shows memory operations
    enable_pruning=True
)
```

Output shows:
- When steps are added
- When pruning occurs
- What steps are removed
- Final message count
