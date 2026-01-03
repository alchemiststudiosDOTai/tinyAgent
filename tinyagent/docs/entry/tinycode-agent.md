---
title: TinyCodeAgent
path: tinyagent/agents/code.py
type: file
depth: 1
description: Python code execution agent with sandboxed environments
exports:
  - TinyCodeAgent
  - PythonExecutor
  - TrustLevel
seams: [E]
---

# TinyCodeAgent

A Python-executing ReAct agent that solves tasks by writing and executing Python code in a sandboxed environment.

## Class Definition

```python
class TinyCodeAgent(BaseAgent):
    """Python-executing ReAct agent with configurable trust levels."""
```

## Initialization Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tools` | `Sequence[Tool]` | `[]` | Available tools (sync only) |
| `model` | `str` | `"gpt-4o-mini"` | LLM model identifier |
| `api_key` | `str \| None` | `None` | API key (defaults to env var) |
| `trust_level` | `TrustLevel` | `TrustLevel.LOCAL` | Execution isolation level |
| `limits` | `ExecutionLimits` | `ExecutionLimits()` | Resource constraints |
| `extra_imports` | `list[str]` | `[]` | Additional allowed imports |
| `system_suffix` | `str \| None` | `None` | Additional system prompt text |
| `prompt_file` | `str \| None` | `None` | Custom prompt file path |
| `memory_manager` | `MemoryManager \| None` | `None` | Conversation memory manager |
| `enable_pruning` | `bool` | `False` | Enable memory pruning |
| `prune_keep_last` | `int` | `3` | Steps to keep when pruning |

## Trust Levels

Available via `TrustLevel` enum:

### `LOCAL` (Default)
- Runs code in current process
- Restricted builtins and imports
- Fastest execution
- Lowest isolation

### `ISOLATED`
- Runs code in subprocess
- Separate process space
- Better fault isolation
- Moderate overhead

### `SANDBOXED`
- Runs code in Docker container
- Full filesystem isolation
- Network restrictions possible
- Highest security
- Slowest execution

## Execution Limits

Configure via `ExecutionLimits`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout_seconds` | `float` | `30.0` | Maximum execution time |
| `max_output_bytes` | `int` | `10000` | Truncate stdout/stderr |
| `max_steps` | `int` | `100` | Maximum execution steps |

## Public Methods

### `async run(task: str, max_steps: int = 10, verbose: bool = False, return_result: bool = False)`

Main execution loop for code-writing agent.

**Parameters:**
- `task` - User task to solve with code
- `max_steps` - Maximum code iterations (default: 10)
- `verbose` - Enable debug logging
- `return_result` - Return `RunResult` object

**Returns:** `str | RunResult`

### `run_sync(*args, **kwargs)`

Synchronous wrapper using `asyncio.run()`.

## Tool Integration

Unlike `ReactAgent`, tools are **injected directly into the Python execution environment**:

```python
# Tool becomes available as global function in agent's code
@tool
def calculate(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

agent = TinyCodeAgent(tools=[calculate])
# Agent can now write: result = calculate(5, 3)
```

**Limitations:**
- Only synchronous tools supported
- Tools must be serializable
- No async operations in generated code

## Memory System

### Scratchpad (`AgentMemory`)
Persistent working memory across execution steps:
```python
agent.memory.store("observation", "Data is CSV format")
value = agent.memory.recall("observation")
```

### Conversation Memory (`MemoryManager`)
Manages structured steps with optional pruning:
- `SystemPromptStep` - System instructions
- `TaskStep` - User task
- `ActionStep` - Code execution with result
- Pruning strategies for long conversations

## Signals

Cognitive primitives injected into execution environment:

```python
# Available in agent's generated code
uncertain("Data format is unclear")
explore("Testing CSV parsing assumptions")
commit("Final answer: 42")
```

Signals are collected and provide visibility into reasoning process.

## Expected Code Format

Agent should output code blocks with `final_answer()` call:

```python
```python
# Analysis and calculations
result = calculate()

# Final answer must be called
final_answer(result)
```
```

## Usage Example

```python
from tinyagent import TinyCodeAgent, TrustLevel, ExecutionLimits

agent = TinyCodeAgent(
    model="gpt-4o",
    trust_level=TrustLevel.ISOLATED,
    limits=ExecutionLimits(
        timeout_seconds=60.0,
        max_output_bytes=50000
    ),
    extra_imports=["pandas", "numpy"]
)

result = agent.run_sync(
    "Read data.csv, calculate the mean of column 'value', "
    "and return the result"
)
print(result)
```

## Safety Considerations

### Local Execution
- Restricts builtins to safe subset
- Controls import whitelist
- Executes in same process

### Isolated Execution
- Subprocess separation
- Cannot affect host process
- Still needs trust in code

### Sandboxed Execution
- Docker container isolation
- Full filesystem protection
- Network control possible
- Best for untrusted code

## Configuration Notes

- `extra_imports` expands default allowed imports (use carefully)
- `enable_pruning` helps with long conversations
- `system_suffix` appends to default system prompt
- Custom prompts can change code format expectations
- Lower `trust_level` = faster but less secure
- Higher `trust_level` = slower but more secure
