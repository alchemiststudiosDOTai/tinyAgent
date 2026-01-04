---
title: Types and Exceptions
path: tinyagent/core/
type: directory
depth: 2
description: Core types, exceptions, and result objects
exports:
  - RunResult
  - FinalAnswer
  - Finalizer
  - StepLimitReached
  - MultipleFinalAnswers
  - InvalidFinalAnswer
  - ToolDefinitionError
  - ToolValidationError
seams: [E]
---

# Types and Exceptions

Core data types and exception classes for agent execution and error handling.

## Core Types

### RunResult

Complete execution result with metrics and metadata.

#### Definition

```python
@dataclass(frozen=True)
class RunResult:
    """Complete result of agent execution."""
    output: str                    # Final output string
    final_answer: FinalAnswer      # Structured final answer
    state: Literal[                # Execution state
        "completed",
        "step_limit_reached",
        "error"
    ]
    steps_taken: int               # Number of steps used
    duration_seconds: float        # Execution time
    error: Exception | None        # Error if failed
    metadata: dict                 # Custom tracking data
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `output` | `str` | Final output string |
| `final_answer` | `FinalAnswer` | Structured answer with metadata |
| `state` | `str` | Execution completion state |
| `steps_taken` | `int` | Number of reasoning steps |
| `duration_seconds` | `float` | Total execution time |
| `error` | `Exception \| None` | Exception if failed |
| `metadata` | `dict` | Custom metadata for tracking |

#### Usage Example

```python
from tinyagent import ReactAgent

agent = ReactAgent(return_result=True)
result: RunResult = agent.run_sync(
    "What's the weather?",
    return_result=True
)

print(f"Output: {result.output}")
print(f"State: {result.state}")
print(f"Steps: {result.steps_taken}")
print(f"Duration: {result.duration_seconds}s")

if result.error:
    print(f"Error: {result.error}")
```

#### State Values

- **`"completed"`** - Agent completed successfully
- **`"step_limit_reached"`** - Max steps exceeded
- **`"error"`** - Exception during execution

### FinalAnswer

Structured final answer with source tracking.

#### Definition

```python
@dataclass(frozen=True)
class FinalAnswer:
    """Final answer with metadata."""
    value: str                              # Answer content
    source: Literal["normal", "final_attempt"]  # Answer source
    timestamp: datetime                     # When answer was set
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `value` | `str` | Answer content |
| `source` | `str` | How answer was generated |
| `timestamp` | `datetime` | When answer was set |

#### Source Values

- **`"normal"`** - Standard execution path
- **`"final_attempt"`** - Last-ditch fallback

#### Usage Example

```python
from tinyagent import ReactAgent

agent = ReactAgent()
result = agent.run_sync("What's 2+2?", return_result=True)

print(f"Answer: {result.final_answer.value}")
print(f"Source: {result.final_answer.source}")
print(f"Time: {result.final_answer.timestamp}")
```

### Finalizer

Manager for idempotent final answer setting.

#### Definition

```python
class Finalizer:
    """Manage final answer with idempotency."""

    def set(self, value: str, source: str = "normal") -> FinalAnswer:
        """Set final answer (can only be called once)."""

    def get(self) -> FinalAnswer | None:
        """Get current final answer."""

    def is_set(self) -> bool:
        """Check if final answer has been set."""
```

#### Methods

##### `set(value: str, source: str = "normal") -> FinalAnswer`
Set final answer (idempotent - can only be called once).

**Parameters:**
- `value` - Final answer content
- `source` - How answer was generated

**Returns:** `FinalAnswer` object

**Raises:** `MultipleFinalAnswers` if called more than once

**Example:**
```python
finalizer = Finalizer()

# First call succeeds
answer = finalizer.set("The answer is 42")

# Second call raises exception
try:
    finalizer.set("Different answer")
except MultipleFinalAnswers:
    print("Can only set final answer once")
```

##### `get() -> FinalAnswer | None`
Get current final answer if set.

**Returns:** `FinalAnswer` or `None`

**Example:**
```python
finalizer = Finalizer()
answer = finalizer.get()  # None

finalizer.set("42")
answer = finalizer.get()  # FinalAnswer(value="42", ...)
```

##### `is_set() -> bool`
Check if final answer has been set.

**Returns:** `bool` indicating if answer is set

**Example:**
```python
finalizer = Finalizer()
print(finalizer.is_set())  # False

finalizer.set("42")
print(finalizer.is_set())  # True
```

## Exceptions

### StepLimitReached

Raised when agent exceeds maximum allowed steps.

#### Definition

```python
class StepLimitReached(Exception):
    """Maximum reasoning steps exceeded."""
    pass
```

#### When Raised

```python
from tinyagent import StepLimitReached, ReactAgent

agent = ReactAgent(max_steps=5)
# Agent runs for 5 steps without answer
# Raises StepLimitReached
```

#### Handling

```python
try:
    result = agent.run_sync(
        "Complex task",
        max_steps=10
    )
except StepLimitReached:
    print("Agent couldn't complete in 10 steps")
    # Try with more steps or different approach
```

### MultipleFinalAnswers

Raised when agent attempts to set final answer multiple times.

#### Definition

```python
class MultipleFinalAnswers(Exception):
    """Final answer can only be set once."""
    pass
```

#### When Raised

```python
from tinyagent import MultipleFinalAnswers, Finalizer

finalizer = Finalizer()
finalizer.set("First answer")

try:
    finalizer.set("Second answer")
except MultipleFinalAnswers:
    print("Cannot set final answer twice")
```

#### Purpose

Enforces idempotency - final answer can only be set once per execution.

### InvalidFinalAnswer

Raised when final answer fails validation.

#### Definition

```python
class InvalidFinalAnswer(Exception):
    """Final answer validation failed."""
    pass
```

#### When Raised

```python
# Agent provides malformed answer
# Expected JSON but got plain text
# Missing required fields
# Wrong format for structured output
```

#### Example

```python
from tinyagent import InvalidFinalAnswer

try:
    # Validate answer format
    if not is_valid_json(answer):
        raise InvalidFinalAnswer(
            "Answer must be valid JSON"
        )
except InvalidFinalAnswers:
    print("Answer format validation failed")
```

### ToolDefinitionError

Raised when `@tool` decorator validation fails.

#### Definition

```python
class ToolDefinitionError(Exception):
    """Tool decorator validation failed."""
    pass
```

#### When Raised

```python
from tinyagent import tool, ToolDefinitionError

# Missing type hints
try:
    @tool
    def bad_func(x, y):  # No type hints
        return x + y
except ToolDefinitionError as e:
    print(f"Tool definition error: {e}")
```

#### Validation Rules

- All parameters must have type hints
- Return type is required
- Function must be callable
- Name must be a valid identifier

### ToolValidationError

Raised when tool class validation fails.

#### Definition

```python
class ToolValidationError(Exception):
    """Tool class validation failed."""
    pass
```

#### When Raised

```python
from tinyagent import validate_tool_class, ToolValidationError

# Tool class uses non-literal defaults
class BadTool:
    def func(self, x: int = default_value):  # Non-literal
        return x

try:
    validate_tool_class(BadTool)
except ToolValidationError as e:
    print(f"Tool validation error: {e}")
```

#### Validation Rules

- Default values must be literals
- No undefined names in defaults
- Class must be simple and serializable
- AST-based static analysis

## Exception Hierarchy

```
Exception
├── StepLimitReached
│   └── Agent execution exceeded max steps
├── MultipleFinalAnswers
│   └── Final answer set multiple times
├── InvalidFinalAnswer
│   └── Final answer validation failed
├── ToolDefinitionError
│   └── Tool decorator validation failed
└── ToolValidationError
    └── Tool class validation failed
```

## Usage Patterns

### Comprehensive Error Handling

```python
from tinyagent import (
    ReactAgent,
    StepLimitReached,
    InvalidFinalAnswer,
    ToolDefinitionError
)

agent = ReactAgent(tools=[my_tool])

try:
    result = agent.run_sync(
        "Solve this problem",
        max_steps=20
    )
except StepLimitReached:
    print("Need more steps or simpler task")
except InvalidFinalAnswer:
    print("Answer format was incorrect")
except ToolDefinitionError:
    print("Tool definition error")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Result State Checking

```python
result = agent.run_sync("Task", return_result=True)

match result.state:
    case "completed":
        print(f"Success: {result.output}")
    case "step_limit_reached":
        print(f"Incomplete: used {result.steps_taken} steps")
    case "error":
        print(f"Error: {result.error}")
```

### Final Answer Idempotency

```python
finalizer = Finalizer()

# Safe to call multiple times if guarded
if not finalizer.is_set():
    finalizer.set("Answer")
    # Only set once

# Or use try/except
try:
    finalizer.set("Answer")
except MultipleFinalAnswers:
    # Already set, use existing
    answer = finalizer.get()
```

## Best Practices

1. **Use `RunResult`** for detailed execution information
2. **Check `state` field** to understand completion status
3. **Handle specific exceptions** for better error messages
4. **Use `Finalizer`** to enforce idempotent final answers
5. **Validate tools early** to fail fast on definition errors
6. **Monitor `steps_taken`** to optimize agent behavior
7. **Use `metadata` field** for custom tracking and analytics
8. **Log exceptions** for debugging and monitoring

## Integration with Agents

### ReactAgent

```python
from tinyagent import ReactAgent

agent = ReactAgent()

# Simple execution
output = agent.run_sync("Question")
# Returns: str

# Detailed result
result = agent.run_sync(
    "Question",
    return_result=True,
    max_steps=10
)
# Returns: RunResult
```

### TinyCodeAgent

```python
from tinyagent import TinyCodeAgent

agent = TinyCodeAgent()

result = agent.run_sync(
    "Calculate mean of [1,2,3,4,5]",
    return_result=True
)

print(f"Steps: {result.steps_taken}")
print(f"Duration: {result.duration_seconds}s")
print(f"State: {result.state}")
```

## Type Checking

```python
from tinyagent import ReactAgent, RunResult

agent = ReactAgent()

# Type-safe usage
result: RunResult = agent.run_sync(
    "Task",
    return_result=True
)

# mypy/pyright will infer correct types
output: str = result.output
steps: int = result.steps_taken
state: Literal["completed", "step_limit_reached", "error"] = result.state
```
