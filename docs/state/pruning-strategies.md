---
title: Pruning Strategies
path: memory/manager.py
type: file
depth: 1
description: Token management strategies for controlling conversation history size
seams: [keep_last_n_steps(), prune_old_observations(), no_pruning()]
---

# Pruning Strategies

## Overview

Pruning strategies are functions that manipulate the conversation history to control token usage. They reduce memory size while preserving essential context for LLM reasoning.

## Strategy Types

### 1. keep_last_n_steps(n: int) -> PruneStrategy

**Purpose**: Keep only the most recent `n` action steps.

**Behavior**:
- Preserves all `SystemPromptStep` instances
- Preserves all `TaskStep` instances
- Keeps last `n` `ActionStep` instances
- Removes all other steps

**Implementation**:
```python
def keep_last_n_steps(n: int) -> PruneStrategy:
    def strategy(steps: list[Step]) -> list[Step]:
        # Always keep system and task steps
        system_task_steps = [s for s in steps if isinstance(s, (SystemPromptStep, TaskStep))]
        # Keep last n action steps
        action_steps = [s for s in steps if isinstance(s, ActionStep)][-n:]
        return system_task_steps + action_steps
    return strategy
```

**Usage**:
```python
from tinyagent.memory.manager import keep_last_n_steps

# Keep only last 10 actions (plus system/task)
manager.prune(keep_last_n_steps(10))
```

**Use Cases**:
- Long-running agents with many actions
- Token-limited scenarios
- Recent context is most important

**Considerations**:
- Irreversible: Pruned steps cannot be recovered
- Context loss: Older information removed entirely
- System preservation: System prompt always maintained

### 2. prune_old_observations(keep_last_n: int, max_length: int) -> PruneStrategy

**Purpose**: Truncate observation content in older steps.

**Behavior**:
- Preserves all `SystemPromptStep` instances
- Preserves all `TaskStep` instances
- Keeps last `keep_last_n` `ActionStep` instances unchanged
- Truncates `observation` field in older `ActionStep` instances to `max_length`

**Implementation**:
```python
def prune_old_observations(keep_last_n: int, max_length: int) -> PruneStrategy:
    def strategy(steps: list[Step]) -> list[Step]:
        result = []
        action_steps = [s for s in steps if isinstance(s, ActionStep)]
        recent_actions = action_steps[-keep_last_n:] if keep_last_n > 0 else []

        for step in steps:
            if isinstance(step, (SystemPromptStep, TaskStep)):
                result.append(step)
            elif isinstance(step, ActionStep):
                if step in recent_actions:
                    result.append(step)  # Keep recent actions intact
                else:
                    # Truncate old observations
                    step.truncate(max_length)
                    result.append(step)
            else:
                result.append(step)

        return result
    return strategy
```

**Usage**:
```python
from tinyagent.memory.manager import prune_old_observations

# Keep last 5 actions intact, truncate older observations to 200 chars
manager.prune(prune_old_observations(keep_last_n=5, max_length=200))
```

**Use Cases**:
- Very large observations (file reads, API responses)
- Need to preserve step structure but reduce content
- Recent observations need full detail

**Considerations**:
- Loss of detail: Truncated observations lose information
- Step preservation: Step structure maintained
- Selective: Only affects ActionStep observations

### 3. no_pruning() -> PruneStrategy

**Purpose**: Identity function that performs no pruning.

**Behavior**:
- Returns steps unchanged
- Useful for testing or debugging

**Implementation**:
```python
def no_pruning() -> PruneStrategy:
    return lambda steps: steps
```

**Usage**:
```python
from tinyagent.memory.manager import no_pruning

# Disable pruning for debugging
manager.prune(no_pruning())
```

**Use Cases**:
- Testing and debugging
- Unlimited token scenarios
- Full history preservation

## Integration with Agents

### TinyCodeAgent

**Location**: `agents/code.py`

**Usage**:
```python
# In _add_observation method
if self.enable_pruning:
    self.memory_manager.prune(keep_last_n_steps(self.pruning_threshold))
```

**Configuration**:
```python
@dataclass
class TinyCodeAgent:
    enable_pruning: bool = True
    pruning_threshold: int = 10  # Keep last 10 actions
```

**Pruning Trigger**:
- After each action observation
- Controlled by `enable_pruning` flag
- Uses configurable threshold

### ReactAgent

**Location**: `agents/react.py`

**Usage**:
- Uses simpler `Memory` class (direct message list)
- No built-in pruning strategies
- Relies on `max_tokens` parameter for response limits

## Pruning Strategy Design

### Step Type Hierarchy

```
Step (base)
├── SystemPromptStep (always preserved)
├── TaskStep (always preserved)
├── ActionStep (prunable)
└── ScratchpadStep (not currently pruned)
```

### Preservation Rules

1. **SystemPromptStep**: Never pruned (critical for behavior)
2. **TaskStep**: Never pruned (essential for context)
3. **ActionStep**: Primary target for pruning
4. **ScratchpadStep**: Not currently handled by strategies

## Token Estimation

### Current Approach
- No explicit token counting
- Relies on step count heuristics
- Assumes step count correlates with token usage

### Limitations
- Variable observation sizes: Some actions have very large observations
- Different models: Tokenization varies by LLM provider
- No feedback loop: No actual token counting to validate strategies

### Potential Improvements
```python
def token_aware_pruning(max_tokens: int) -> PruneStrategy:
    def strategy(steps: list[Step]) -> list[Step]:
        # Count actual tokens using tiktoken
        total_tokens = 0
        result = []

        for step in reversed(steps):
            step_tokens = count_tokens(step)
            if total_tokens + step_tokens > max_tokens:
                break
            result.insert(0, step)
            total_tokens += step_tokens

        return result
    return strategy
```

## Pruning Best Practices

### 1. Choose Strategy Based on Use Case

**Recent context important**:
```python
manager.prune(keep_last_n_steps(5))
```

**Large observations**:
```python
manager.prune(prune_old_observations(keep_last_n=3, max_length=100))
```

**Debugging**:
```python
manager.prune(no_pruning())
```

### 2. Configure Thresholds Appropriately

```python
# Conservative pruning (more context)
manager.prune(keep_last_n_steps(20))

# Aggressive pruning (fewer tokens)
manager.prune(keep_last_n_steps(5))

# Balanced approach
manager.prune(prune_old_observations(keep_last_n=10, max_length=500))
```

### 3. Monitor Token Usage

```python
# Estimate tokens before/after pruning
before = count_tokens(manager.to_messages())
manager.prune(keep_last_n_steps(10))
after = count_tokens(manager.to_messages())

print(f"Token reduction: {before} -> {after} ({(after/before)*100:.1f}%)")
```

### 4. Test Pruning Impact

```python
# Test different strategies
strategies = [
    keep_last_n_steps(5),
    keep_last_n_steps(10),
    prune_old_observations(5, 200)
]

for strategy in strategies:
    test_manager = copy.deepcopy(manager)
    test_manager.prune(strategy)
    # Evaluate performance/quality
```

## Advanced Strategies

### Custom Strategy: Keep Important Steps

```python
def keep_important_steps(importance_fn: Callable[[Step], float], n: int) -> PruneStrategy:
    def strategy(steps: list[Step]) -> list[Step]:
        # Always keep system/task
        system_task = [s for s in steps if isinstance(s, (SystemPromptStep, TaskStep))]

        # Score action steps by importance
        actions = [s for s in steps if isinstance(s, ActionStep)]
        scored = [(importance_fn(s), s) for s in actions]
        scored.sort(reverse=True)

        # Keep top n important
        top_actions = [s for score, s in scored[:n]]
        return system_task + top_actions
    return strategy
```

### Custom Strategy: Semantic Pruning

```python
def semantic_pruning(max_tokens: int) -> PruneStrategy:
    def strategy(steps: list[Step]) -> list[Step]:
        # Use embeddings to select semantically diverse steps
        # Preserves system/task, selects diverse action steps
        # Implementation would use sentence-transformers or similar
        pass
    return strategy
```

## Execution Limits

**Location**: `limits/boundaries.py`

**Complementary to Pruning**: `ExecutionLimits` controls output size from tool execution.

```python
@dataclass
class ExecutionLimits:
    max_output_bytes: int = 100_000  # 100KB default

    def truncate_output(self, output: str) -> tuple[str, bool]:
        if len(output.encode('utf-8')) > self.max_output_bytes:
            truncated = output[:self.max_output_bytes] + "\n[OUTPUT TRUNCATED]"
            return truncated, True
        return output, False
```

**Usage**:
```python
# In TinyCodeAgent
truncated_output, was_truncated = self.limits.truncate_output(raw_output)

# In LocalExecutor
truncated, _ = limits.truncate_output(output)
```

**Relationship to Pruning**:
- Pruning: Controls conversation history size
- Execution limits: Controls individual output size
- Both work together to manage tokens

## Monitoring and Debugging

### Track Pruning Events

```python
class PruningTracker:
    def __init__(self):
        self.pruning_events = []

    def track_pruning(self, before_count: int, after_count: int, strategy: str):
        self.pruning_events.append({
            "timestamp": time.time(),
            "before": before_count,
            "after": after_count,
            "strategy": strategy,
            "reduction": before_count - after_count
        })

# Usage
tracker = PruningTracker()
before = len(manager.steps)
manager.prune(keep_last_n_steps(10))
after = len(manager.steps)
tracker.track_pruning(before, after, "keep_last_n_steps(10)")
```

### Log Pruning Decisions

```python
def logged_pruning(strategy: PruneStrategy, name: str) -> PruneStrategy:
    def wrapper(steps: list[Step]) -> list[Step]:
        before = len(steps)
        result = strategy(steps)
        after = len(result)
        logger.info(f"Pruning '{name}': {before} -> {after} steps")
        return result
    return wrapper

# Usage
manager.prune(logged_pruning(keep_last_n_steps(10), "keep_10"))
```

## Recommendations

1. **Start conservative**: Use higher thresholds initially
2. **Monitor quality**: Track agent performance with different strategies
3. **Test thoroughly**: Validate pruning doesn't break reasoning
4. **Document choices**: Record why specific strategies were chosen
5. **Consider tokens**: Move toward token-aware strategies
