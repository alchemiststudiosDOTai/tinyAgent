---
title: tinyagent Root Package
path: tinyagent/__init__.py
type: file
depth: 0
description: Main package entry point exporting all public APIs
exports:
  - ReactAgent
  - TinyCodeAgent
  - TrustLevel
  - Executor
  - ExecutionResult
  - LocalExecutor
  - PythonExecutor
  - ExecutionLimits
  - ExecutionTimeout
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
  - uncertain
  - explore
  - commit
  - tool
  - validate_tool_class
  - ToolCallingMode
  - FinalAnswer
  - RunResult
  - Finalizer
  - StepLimitReached
  - MultipleFinalAnswers
  - InvalidFinalAnswer
  - ToolDefinitionError
  - ToolValidationError
seams: [E]
---

# tinyagent Root Package

The root package (`tinyagent/__init__.py`) serves as the primary entry point for the framework, auto-loading environment variables and re-exporting all public APIs.

## Auto-Environment Loading

On import, the package automatically searches for and loads `.env` files:
```python
from dotenv import find_dotenv, load_dotenv

env_path = find_dotenv()
if env_path:
    load_dotenv(env_path)
```

## Public API Surface

### Agents
- **`ReactAgent`** - JSON tool-calling agent for general-purpose tasks
- **`TinyCodeAgent`** - Python code execution agent with sandboxed environments
- **`TrustLevel`** - Enum for code execution trust levels (local, isolated, sandboxed)

### Execution
- **`Executor`** - Protocol defining code execution backend interface
- **`ExecutionResult`** - Result dataclass from code execution
- **`LocalExecutor`** - Restricted `exec()` backend running in-process
- **`PythonExecutor`** - Alias for LocalExecutor (backwards compatibility)
- **`ExecutionLimits`** - Resource limit configuration (timeout, max_output_bytes, max_steps)
- **`ExecutionTimeout`** - Exception raised when execution exceeds time limits

### Memory System
- **`AgentMemory`** - Working memory/scratchpad for persistent state across steps
- **`MemoryManager`** - Structured conversation history with pruning support
- **`Step`** - Base class for memory steps
- **`SystemPromptStep`** - System prompt message step
- **`TaskStep`** - User task/question step
- **`ActionStep`** - Tool call with observation/error step
- **`ScratchpadStep`** - Working memory notes step
- **`PruneStrategy`** - Type alias for pruning functions
- **`keep_last_n_steps`** - Pruning strategy to keep last N action steps
- **`prune_old_observations`** - Strategy to truncate old observations
- **`no_pruning`** - Identity function (no pruning)

### Signals
- **`uncertain`** - Signal uncertainty during reasoning
- **`explore`** - Signal exploration/investigation
- **`commit`** - Signal confidence and final answer

### Tools
- **`tool`** - Decorator to create Tool objects from functions
- **`validate_tool_class`** - Static analysis validator for tool classes
- **`ToolCallingMode`** - Enum for tool calling adapter modes

### Types
- **`FinalAnswer`** - Final answer with metadata
- **`RunResult`** - Complete execution result with metrics
- **`Finalizer`** - Final answer manager ensuring idempotency

### Exceptions
- **`StepLimitReached`** - Max steps exceeded
- **`MultipleFinalAnswers`** - Multiple final answers attempted
- **`InvalidFinalAnswer`** - Final answer validation failed
- **`ToolDefinitionError`** - Tool decorator validation failed
- **`ToolValidationError`** - Tool class validation failed

## Usage Example

```python
import tinyagent

# All public APIs available directly
agent = tinyagent.ReactAgent(
    model="gpt-4o-mini",
    tools=[my_tool]
)

result = agent.run_sync("What's the weather?")
```
