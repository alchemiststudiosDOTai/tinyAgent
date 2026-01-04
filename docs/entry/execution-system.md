---
title: Execution System
path: tinyagent/execution/
type: directory
depth: 1
description: Code execution backends and resource limit management
exports:
  - Executor
  - ExecutionResult
  - LocalExecutor
  - PythonExecutor
  - ExecutionLimits
  - ExecutionTimeout
seims: [E]
---

# Execution System

Pluggable code execution backends with configurable resource limits for safe Python code execution.

## Architecture

```
Execution System
├── Executor (Protocol)
│   └── Interface definition for backends
├── LocalExecutor
│   └── In-process restricted exec() backend
├── ExecutionResult
│   └── Execution outcome dataclass
└── ExecutionLimits
    └── Resource constraint configuration
```

## Executor Protocol

Abstract interface defining code execution backend requirements.

### Protocol Definition

```python
class Executor(Protocol):
    """Protocol for code execution backends."""

    async def run(
        self,
        code: str,
        timeout: float | None = None
    ) -> ExecutionResult:
        """Execute code and return result."""

    def kill(self) -> None:
        """Terminate execution."""

    def inject(self, name: str, value: Any) -> None:
        """Inject value into execution namespace."""

    def reset(self) -> None:
        """Reset execution state."""
```

### Required Methods

#### `async run(code: str, timeout: float | None = None) -> ExecutionResult`
Execute Python code with optional timeout.

**Parameters:**
- `code` - Python code to execute
- `timeout` - Maximum execution time in seconds

**Returns:** `ExecutionResult` with output/error

**Raises:** `ExecutionTimeout` if timeout exceeded

#### `kill() -> None`
Terminate current execution immediately.

**Use Cases:**
- User interrupts
- Resource exhaustion
- External cancellation

#### `inject(name: str, value: Any) -> None`
Add a variable or function to the execution namespace.

**Use Cases:**
- Provide tool functions
- Inject dependencies
- Set up environment

**Example:**
```python
executor.inject("search_tool", search_function)
# Now code can use: search_tool(query)
```

#### `reset() -> None`
Clear execution state and namespace.

**Use Cases:**
- Clean state between runs
- Remove injected values
- Reset globals

## LocalExecutor

Restricted `exec()` backend running in the same process with limited builtins and imports.

### Class Definition

```python
class LocalExecutor:
    """Restricted in-process code executor."""

    def __init__(
        self,
        limits: ExecutionLimits = ExecutionLimits(),
        extra_imports: list[str] | None = None
    ):
        """Initialize executor with limits."""

    async def run(
        self,
        code: str,
        timeout: float | None = None
    ) -> ExecutionResult:
        """Execute code in restricted environment."""
```

### Initialization Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limits` | `ExecutionLimits` | `ExecutionLimits()` | Resource constraints |
| `extra_imports` | `list[str]` | `None` | Additional allowed imports |

### Security Features

#### Restricted Builtins
Only safe built-in functions available:

```python
SAFE_BUILTINS = {
    "abs", "all", "any", "bin", "bool", "dict",
    "enumerate", "filter", "float", "hex", "int",
    "list", "map", "max", "min", "range", "round",
    "set", "sorted", "str", "sum", "tuple", "zip",
    # ... (safe functions only)
}
```

**Excluded Builtins:**
- `open` - File I/O restricted
- `eval` - Dynamic execution blocked
- `exec` - Nested execution blocked
- `__import__` - Import control enforced
- `globals`, `locals` - Namespace access blocked

#### Import Whitelist

**Default Allowed Imports:**
```python
DEFAULT_IMPORTS = [
    "math", "statistics", "datetime", "random",
    "collections", "itertools", "fractions", "decimal"
]
```

**Extra Imports:**
```python
executor = LocalExecutor(
    extra_imports=["pandas", "numpy", "requests"]
)
```

**Blocked Imports:**
- `os` - System access blocked
- `sys` - System info blocked
- `subprocess` - Process execution blocked
- `socket` - Network access blocked
- `shutil` - File operations blocked

### Usage Example

```python
from tinyagent import LocalExecutor, ExecutionLimits

executor = LocalExecutor(
    limits=ExecutionLimits(timeout_seconds=10.0),
    extra_imports=["pandas", "numpy"]
)

# Inject tools/functions
executor.inject("calculate", lambda x, y: x + y)

# Execute code
result = await executor.run("""
data = [1, 2, 3, 4, 5]
mean = sum(data) / len(data)
print(f"Mean: {mean}")
""")

print(result.output)  # "Mean: 3.0"
print(result.error)   # None if successful
```

## ExecutionResult

Dataclass containing execution outcome information.

### Definition

```python
@dataclass
class ExecutionResult:
    """Result of code execution."""
    output: str              # Stdout captured
    error: str | None        # Error message if failed
    timed_out: bool          # Whether execution timed out
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `output` | `str` | Captured stdout |
| `error` | `str \| None` | Error traceback if exception |
| `timed_out` | `bool` | True if execution exceeded timeout |

### Usage

```python
result = await executor.run(code)

if result.timed_out:
    print("Execution took too long")
elif result.error:
    print(f"Error: {result.error}")
else:
    print(f"Output: {result.output}")
```

## ExecutionLimits

Configuration for resource constraints during code execution.

### Definition

```python
@dataclass
class ExecutionLimits:
    """Resource limits for code execution."""
    timeout_seconds: float = 30.0
    max_output_bytes: int = 10000
    max_steps: int = 100
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout_seconds` | `float` | `30.0` | Maximum execution time |
| `max_output_bytes` | `int` | `10000` | Truncate stdout/stderr |
| `max_steps` | `int` | `100` | Maximum execution steps |

### Usage Examples

```python
from tinyagent import ExecutionLimits, LocalExecutor

# Default limits
executor = LocalExecutor()

# Custom limits
limits = ExecutionLimits(
    timeout_seconds=60.0,
    max_output_bytes=50000,
    max_steps=1000
)
executor = LocalExecutor(limits=limits)
```

### Enforcement

**Timeout:**
```python
# Execution terminates after timeout
try:
    result = await executor.run(
        "while True: pass",
        timeout=5.0
    )
except ExecutionTimeout:
    print("Code timed out")
```

**Output Truncation:**
```python
# Long output truncated to max_output_bytes
result = await executor.run("""
for i in range(1000000):
    print(f"Line {i}")
""")

# Output truncated to max_output_bytes
assert len(result.output) <= limits.max_output_bytes
```

## ExecutionTimeout Exception

Raised when execution exceeds time limits.

### Definition

```python
class ExecutionTimeout(Exception):
    """Code execution exceeded timeout."""
    pass
```

### Handling

```python
from tinyagent import ExecutionTimeout

try:
    result = await executor.run(
        "while True: pass",
        timeout=5.0
    )
except ExecutionTimeout:
    print("Execution timed out after 5 seconds")
    # Clean up or try alternative approach
```

## PythonExecutor

Alias for `LocalExecutor` for backwards compatibility.

```python
from tinyagent import PythonExecutor, LocalExecutor

# Same class
assert PythonExecutor is LocalExecutor
```

## Integration with TinyCodeAgent

### Trust Levels

```python
from tinyagent import TinyCodeAgent, TrustLevel, LocalExecutor

# LOCAL - Uses LocalExecutor directly
agent = TinyCodeAgent(
    trust_level=TrustLevel.LOCAL,
    # Equivalent to:
    # executor=LocalExecutor()
)

# ISOLATED - Uses SubprocessExecutor (future)
# SANDBOXED - Uses DockerExecutor (future)
```

### Executor Configuration

```python
from tinyagent import TinyCodeAgent, ExecutionLimits

agent = TinyCodeAgent(
    limits=ExecutionLimits(
        timeout_seconds=60.0,
        max_output_bytes=50000
    ),
    extra_imports=["pandas", "numpy"]
)
```

### Tool Injection

```python
from tinyagent import TinyCodeAgent, tool

@tool
def calculate(x: float, y: float) -> float:
    """Add two numbers."""
    return x + y

agent = TinyCodeAgent(tools=[calculate])

# Tools injected into executor namespace
# Available in generated code: calculate(5, 3)
```

## Best Practices

1. **Always set timeouts** to prevent infinite loops
2. **Limit output size** to prevent memory exhaustion
3. **Restrict imports** to only necessary modules
4. **Monitor resource usage** in production
5. **Use appropriate trust levels** for your security needs
6. **Test with safe code** before deployment
7. **Consider subprocess/Docker** for untrusted code
8. **Implement rate limiting** for multi-user scenarios

## Security Considerations

### LocalExecutor Security

**Protected:**
- File I/O blocked
- System calls blocked
- Network access blocked
- Process creation blocked

**Risks:**
- Runs in same process
- CPU/memory attacks possible
- Can access injected objects
- Side-channel attacks possible

**Mitigation:**
- Use `extra_imports` carefully
- Validate injected tools
- Monitor resource usage
- Consider isolation for untrusted code

### When to Use Isolation

**Use LocalExecutor for:**
- Trusted code
- Internal tools
- Development/testing
- Low-risk scenarios

**Use Isolation (future) for:**
- User-provided code
- Untrusted input
- Production multi-tenant
- High-security requirements

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `run()` | O(n) | n = code size |
| `inject()` | O(1) | Simple dict insert |
| `reset()` | O(1) | Clear namespace |
| Memory | O(n) | n = variables created |

## Future Backend Support

Planned executors for enhanced isolation:
- `SubprocessExecutor` - Separate process isolation
- `DockerExecutor` - Container-based isolation
- `FirecrackerExecutor` - MicroVM isolation

## Debugging

Enable verbose execution:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

executor = LocalExecutor()
result = await executor.run(code)
# Shows execution details, errors, etc.
```
