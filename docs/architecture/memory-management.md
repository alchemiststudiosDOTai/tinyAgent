---
title: Memory Management Architecture
path: architecture/
type: directory
depth: 0
description: Memory systems, pruning strategies, and state management
seams: [A]
---

# Memory Management Architecture

## Overview

The tinyAgent framework employs a sophisticated two-tier memory architecture that addresses the challenges of limited LLM context windows, long-running conversations, and stateful reasoning. This document details the memory systems, their design patterns, and optimization strategies.

---

## Memory Architecture Overview

### Two-Tier Design

```
┌─────────────────────────────────────────────────┐
│                 Agent Memory                     │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────┐      ┌─────────────────┐ │
│  │ Memory Manager   │      │  Scratchpad     │ │
│  │  (Long-term)     │      │  (Working)      │ │
│  │                  │      │                 │ │
│  │  • SystemPrompt  │      │  • Variables    │ │
│  │  • TaskStep      │      │  • Observations │ │
│  │  • ActionStep    │      │  • Failures     │ │
│  │                  │      │                 │ │
│  │  Prunable        │      │  Transient      │ │
│  └──────────────────┘      └─────────────────┘ │
│         │                           │          │
└─────────┼───────────────────────────┼──────────┘
          │                           │
          ▼                           ▼
    ┌─────────────────┐      ┌─────────────────┐
    │ LLM Context     │      │ Executor        │
    │ (Messages)      │      │ (Namespace)     │
    └─────────────────┘      └─────────────────┘
```

### Design Principles

1. **Separation of Concerns**: Long-term vs. working memory
2. **Prunability**: Memory designed for intelligent truncation
3. **Type Safety**: Structured data classes, not dictionaries
4. **Immutability**: Steps are immutable once created
5. **Observability**: Rich metadata (timestamps, step numbers)

---

## Memory Manager (Long-term Memory)

**Location:** `/Users/tuna/tinyAgent/tinyagent/memory/manager.py`

### Purpose

Structured conversation history that:
- Maintains full agent-LLM interaction trace
- Provides context for LLM reasoning
- Supports intelligent pruning strategies
- Preserves reasoning chain while saving tokens

### Architecture

```python
class MemoryManager:
    def __init__(
        self,
        system_prompt: str | None = None,
        prune_strategy: PruneStrategy | None = None
    ):
        self._steps: list[Step] = []
        self._prune_strategy = prune_strategy or keep_last_n_steps(50)

        if system_prompt:
            self.add(SystemPromptStep(content=system_prompt))

    def add(self, step: Step) -> None:
        """Add a step and track step number"""
        step.step_number = len(self._steps)
        self._steps.append(step)

        # Auto-prune if needed
        if len(self._steps) > 1000:
            self.prune()

    def prune(self) -> None:
        """Apply pruning strategy"""
        self._steps = self._prune_strategy(self._steps)

    def to_messages(self) -> list[Message]:
        """Convert to LLM-compatible format"""
        messages = []
        for step in self._steps:
            messages.extend(step.to_messages())
        return messages
```

### Step Hierarchy

**Location:** `/Users/tuna/tinyAgent/tinyagent/memory/steps.py`

```python
@dataclass
class Step:
    """Base class for all memory steps"""
    timestamp: datetime
    step_number: int

    def to_messages(self) -> list[Message]:
        raise NotImplementedError
```

#### SystemPromptStep

```python
@dataclass
class SystemPromptStep(Step):
    """Initial system prompt defining agent persona"""
    content: str

    def to_messages(self) -> list[Message]:
        return [{"role": "system", "content": self.content}]
```

**Usage:**
```python
memory.add(SystemPromptStep(
    content="You are a helpful coding assistant"
))
```

#### TaskStep

```python
@dataclass
class TaskStep(Step):
    """User task or query"""
    task: str

    def to_messages(self) -> list[Message]:
        return [{"role": "user", "content": self.task}]
```

**Usage:**
```python
memory.add(TaskStep(
    task="Analyze the sales data and create a report"
))
```

#### ActionStep

```python
@dataclass
class ActionStep(Step):
    """Agent action and resulting observation"""
    reasoning: str      # LLM reasoning
    action: str         # Action taken (tool/code)
    observation: str    # Result/output
    signals: list[Signal] = field(default_factory=list)

    def to_messages(self) -> list[Message]:
        return [
            {"role": "assistant", "content": self.reasoning},
            {"role": "user", "content": f"Observation: {self.observation}"}
        ]
```

**Usage:**
```python
memory.add(ActionStep(
    reasoning="I need to search for information",
    action="web_search",
    observation="Found 5 relevant articles",
    signals=[Signal(type="explore", message="Searching web")]
))
```

---

## Pruning Strategies

**Location:** `/Users/tuna/tinyAgent/tinyagent/memory/manager.py`

### Strategy Pattern

```python
from typing import Callable

PruneStrategy = Callable[[list[Step]], list[Step]]
```

### Built-in Strategies

#### 1. Keep Last N Steps

```python
def keep_last_n_steps(n: int) -> PruneStrategy:
    """Keep only the most recent N steps"""
    def prune(steps: list[Step]) -> list[Step]:
        return steps[-n:] if len(steps) > n else steps
    return prune
```

**Use Case:** Simple token management

**Trade-offs:**
- Pro: Predictable memory size
- Con: Loses early context

---

#### 2. Prune Old Observations

```python
def prune_old_observations(max_age_seconds: int) -> PruneStrategy:
    """Truncate observation text in old steps"""
    def prune(steps: list[Step]) -> list[Step]:
        now = time.time()
        pruned = []

        for step in steps:
            if isinstance(step, ActionStep):
                age = now - step.timestamp.timestamp()
                if age > max_age_seconds:
                    # Truncate observation but keep step
                    step.observation = step.observation[:100] + "..."
            pruned.append(step)

        return pruned
    return prune
```

**Use Case:** Long-running tasks with full history

**Trade-offs:**
- Pro: Keeps reasoning chain intact
- Con: Still uses tokens for structure

---

#### 3. Keep System and Recent

```python
def keep_system_and_recent(n_recent: int) -> PruneStrategy:
    """Always keep system prompt, then last N steps"""
    def prune(steps: list[Step]) -> list[Step]:
        system_steps = [s for s in steps if isinstance(s, SystemPromptStep)]
        recent_steps = steps[-n_recent:] if len(steps) > n_recent else steps
        return system_steps + recent_steps
    return prune
```

**Use Case:** System prompt is critical

**Trade-offs:**
- Pro: Never loses persona
- Con: System prompt uses tokens

---

#### 4. Semantic Pruning (Advanced)

```python
def semantic_pruning(embedder: Embedder, max_tokens: int) -> PruneStrategy:
    """Use embeddings to keep semantically diverse steps"""
    def prune(steps: list[Step]) -> list[Step]:
        # 1. Embed all steps
        embeddings = [embedder.embed(step) for step in steps]

        # 2. Calculate diversity score
        # 3. Select steps that maximize diversity
        # 4. Ensure recent steps are prioritized
        ...

    return prune
```

**Use Case:** Complex multi-step reasoning

**Status:** Not implemented (future work)

---

### Creating Custom Strategies

```python
def custom_strategy(min_steps: int, max_tokens: int) -> PruneStrategy:
    """Custom pruning logic"""
    def prune(steps: list[Step]) -> list[Step]:
        # 1. Always keep system prompt
        # 2. Always keep last N steps
        # 3. Fill middle with token budget
        ...

    return prune

# Usage
memory = MemoryManager(prune_strategy=custom_strategy(10, 4000))
```

---

## Scratchpad Memory (Working Memory)

**Location:** `/Users/tuna/tinyAgent/tinyagent/memory/scratchpad.py`

### Purpose

Transient working memory for `TinyCodeAgent` that:
- Stores variables between code executions
- Logs observations for LLM context
- Tracks failed attempts
- Provides persistent state during agent run

### Architecture

```python
class AgentMemory:
    """Working memory for code-executing agents"""

    def __init__(self):
        self._store: dict[str, Any] = {}
        self._observations: list[str] = []
        self._failures: list[str] = []

    # Store/recall pattern
    def store(self, key: str, value: Any) -> None:
        """Store a variable for later recall"""
        self._store[key] = value

    def recall(self, key: str) -> Any:
        """Recall a stored variable"""
        return self._store.get(key)

    # Observation logging
    def observe(self, observation: str) -> None:
        """Log an observation"""
        self._observations.append(observation)

    # Failure tracking
    def fail(self, error: str) -> None:
        """Record a failed attempt"""
        self._failures.append(error)

    # Context export
    def to_context(self) -> str:
        """Export memory as context string"""
        parts = []

        if self._store:
            parts.append("Stored Variables:")
            for key, value in self._store.items():
                parts.append(f"  {key}: {value}")

        if self._observations:
            parts.append("Observations:")
            for obs in self._observations[-5:]:  # Last 5
                parts.append(f"  - {obs}")

        if self._failures:
            parts.append("Failed Attempts:")
            for fail in self._failures[-3:]:  # Last 3
                parts.append(f"  - {fail}")

        return "\n".join(parts)
```

### Usage in Code Execution

```python
# Injected into executor namespace
executor = LocalExecutor()
executor.inject("store", memory.store)
executor.inject("recall", memory.recall)
executor.inject("observe", memory.observe)
executor.inject("fail", memory.fail)

# LLM can write code that uses scratchpad
code = """
store("user_id", 12345)
store("username", "john_doe")
observe("Found user in database")

# Later in another iteration
user = recall("user_id")
print(f"Processing user {user}")
"""
```

### Context Integration

```python
# After code execution, scratchpad context is added to observation
output = await executor.run(code)
full_observation = f"{output}\n\n{scratchpad.to_context()}"

# LLM sees:
# stdout output...
#
# Stored Variables:
#   user_id: 12345
#   username: john_doe
# Observations:
#   - Found user in database
```

---

## Memory Lifecycle

### ReactAgent Memory (Simple)

```python
# 1. Initialization
memory = Memory()
memory.add("system", system_prompt)
memory.add("user", task)

# 2. During loop
while not done:
    # Convert to messages
    messages = memory.to_list()

    # LLM call
    response = await llm(messages)

    # Add tool call
    memory.add("assistant", reasoning, tool_call=call)

    # Execute tool
    result = await tool.run(**args)

    # Add result
    memory.add("tool", result, tool_call_id=call.id)

# 3. Return
return final_answer
```

### TinyCodeAgent Memory (Structured)

```python
# 1. Initialization
memory_manager = MemoryManager()
memory_manager.add(SystemPromptStep(content=system_prompt))
memory_manager.add(TaskStep(task=user_task))

scratchpad = AgentMemory()

# 2. During loop
while not done:
    # Convert to messages
    messages = memory_manager.to_messages()

    # LLM call
    response = await llm(messages)

    # Extract code
    code = extract_code(response)

    # Execute with scratchpad
    output = await executor.run(code)

    # Create action step
    action_step = ActionStep(
        reasoning=response.reasoning,
        action="code_execution",
        code=code,
        observation=output,
        signals=collected_signals
    )

    # Add to memory
    memory_manager.add(action_step)

    # Check completion
    if finalizer.is_set:
        done = True

# 3. Return
return finalizer.answer
```

---

## Token Management

### Token Counting

```python
import tiktoken

def count_tokens(messages: list[Message]) -> int:
    """Count tokens in messages"""
    encoding = tiktoken.encoding_for_model("gpt-4")
    total = 0

    for message in messages:
        total += len(encoding.encode(message["content"]))

    return total
```

### Adaptive Pruning

```python
class AdaptiveMemoryManager(MemoryManager):
    """Automatically prune based on token count"""

    def __init__(self, max_tokens: int = 4000):
        super().__init__()
        self._max_tokens = max_tokens

    def to_messages(self) -> list[Message]:
        """Prune until under token limit"""
        messages = super().to_messages()

        while count_tokens(messages) > self._max_tokens:
            self.prune()
            messages = super().to_messages()

        return messages
```

---

## Memory Patterns

### Pattern 1: Sliding Window

```python
# Keep last N steps
memory = MemoryManager(
    prune_strategy=keep_last_n_steps(50)
)
```

**Best for:**
- Short conversations
- Limited context needs
- Predictable token usage

---

### Pattern 2: Summarization

```python
def summarize_strategy(summarizer: Callable) -> PruneStrategy:
    """Summarize old steps"""
    def prune(steps: list[Step]) -> list[Step]:
        if len(steps) > 50:
            old_steps = steps[:-25]
            recent_steps = steps[-25:]

            # Summarize old steps
            summary = summarizer(old_steps)

            # Replace with single summary step
            summary_step = TaskStep(task=f"[Summary] {summary}")
            return [summary_step] + recent_steps

        return steps
    return prune
```

**Best for:**
- Long conversations
- Preserving early context
- Multi-phase tasks

---

### Pattern 3: Hierarchical Memory

```python
class HierarchicalMemory:
    """Multi-level memory hierarchy"""

    def __init__(self):
        self.short_term = MemoryManager()  # Last 20 steps
        self.medium_term = MemoryManager()  # Summarized chunks
        self.long_term = MemoryManager()   # Key milestones

    def add(self, step: Step) -> None:
        self.short_term.add(step)

        # Promote to medium term
        if len(self.short_term._steps) > 20:
            summary = self._summarize(self.short_term._steps)
            self.medium_term.add(TaskStep(task=summary))
            self.short_term.prune()
```

**Best for:**
- Very long-running agents
- Complex multi-stage reasoning
- Maintaining global context

---

## Debugging Memory

### Memory Inspection

```python
# Print memory state
def debug_memory(memory: MemoryManager):
    print(f"Total steps: {len(memory._steps)}")
    print(f"Token count: {count_tokens(memory.to_messages())}")

    for step in memory._steps:
        print(f"{step.step_number}: {type(step).__name__}")
        if isinstance(step, ActionStep):
            print(f"  Action: {step.action}")
            print(f"  Obs length: {len(step.observation)}")
```

### Memory Visualization

```python
def visualize_memory(memory: MemoryManager) -> str:
    """Create ASCII visualization"""
    lines = ["Memory Layout:"]

    for i, step in enumerate(memory._steps):
        step_type = type(step).__name__
        if isinstance(step, ActionStep):
            obs_len = len(step.observation)
            lines.append(f"  [{i}] {step_type} (obs: {obs_len} chars)")
        else:
            lines.append(f"  [{i}] {step_type}")

    return "\n".join(lines)
```

---

## Performance Considerations

### Memory Overhead

| Operation | Cost | Optimization |
|-----------|------|--------------|
| Add step | O(1) | None needed |
| Prune | O(n) | Prune less frequently |
| to_messages | O(n) | Cache result |
| Token count | O(n) | Estimate, don't count |

### Optimization Strategies

1. **Lazy Token Counting:**
   ```python
   # Count only when needed
   if self._token_count is None:
       self._token_count = count_tokens(self.to_messages())
   ```

2. **Batch Pruning:**
   ```python
   # Prune every N steps, not every step
   if len(self._steps) % 10 == 0:
       self.prune()
   ```

3. **Caching:**
   ```python
   # Cache message conversion
   if self._cached_messages is None:
       self._cached_messages = self.to_messages()
   ```

---

## Related Documentation

- **Agent Hierarchy**: `/docs/architecture/agent-hierarchy.md`
- **Data Flow**: `/docs/architecture/data-flow.md`
- **Design Patterns**: `/docs/architecture/design-patterns.md`
- **Code Execution**: `/docs/architecture/code-execution.md`
