---
title: Design Patterns
path: architecture/
type: directory
depth: 0
description: Architectural and design patterns used throughout the framework
seams: [A]
---

# Design Patterns

## Overview

The tinyAgent framework employs a collection of classical and agent-specific design patterns to achieve modularity, extensibility, and safety. This document catalogs the key patterns and their implementations.

---

## Agent Patterns

### ReAct (Reason+Act) Pattern

**Used By:** `ReactAgent`, `TinyCodeAgent`

**Description:** The foundational pattern for both agent types, combining reasoning and acting in an iterative loop.

#### ReactAgent Implementation

Classic ReAct loop with explicit reasoning and action phases:

```python
while not done:
    # Reason: LLM generates thoughts
    response = await self._chat(messages)

    # Act: Either call tool or answer
    if "tool" in response:
        result = await self._execute_tool(response["tool"], response["arguments"])
        messages.append(result)
    else:
        done = True
        return response["answer"]
```

**Characteristics:**
- Scratchpad-based reasoning (visible in conversation history)
- JSON-structured actions
- Iterative observation-reasoning-action cycle

#### TinyCodeAgent Implementation

Code-centric adaptation where reasoning and action are unified in Python code:

```python
while not done:
    # Generate: LLM writes Python code with reasoning in comments
    code = await self._chat(messages)

    # Execute: Run code (reasoning + action combined)
    output = await self._executor.run(code)

    # Check: Did code call final_answer()?
    if self._finalizer.is_set:
        done = True
        return self._finalizer.answer
```

**Characteristics:**
- Reasoning embedded in code comments
- Actions are Python function calls
- Unified reasoning-action step

---

## Structural Patterns

### Adapter Pattern

**Location:** `/Users/tuna/tinyAgent/tinyagent/core/adapters.py`

**Purpose:** Decouple agent logic from specific LLM tool-calling implementations.

### The Problem

Different LLMs have different tool-calling mechanisms:
- **Native**: GPT-4, Claude (function calling API)
- **Structured JSON**: Models that can output valid JSON
- **Text parsing**: Older models requiring manual parsing

### The Solution

Define a `ToolCallingAdapter` protocol with concrete implementations:

```python
class ToolCallingAdapter(Protocol):
    async def format_request(self, tools: list[Tool]) -> dict[str, Any]:
        """Format tools for LLM request"""
        ...

    async def extract_tool_call(self, response: Any) -> ToolCall | None:
        """Extract tool call from LLM response"""
        ...
```

**Implementations:**

1. **NativeToolAdapter**: Uses model's native function calling
   ```python
   # GPT-4: tools parameter in API request
   response = await client.chat.completions.create(
       tools=[tool.schema for tool in tools]
   )
   ```

2. **OpenAIStructuredAdapter**: Uses structured JSON output mode
   ```python
   # Force JSON response format
   response = await client.chat.completions.create(
       response_format={"type": "json_object"}
   )
   ```

3. **ValidatedAdapter**: Wraps any adapter with Pydantic validation
   ```python
   # Add runtime type checking
   call = adapter.extract_tool_call(response)
   validated = self._validate_arguments(call, tool_schema)
   ```

### Factory Pattern

**Location:** `/Users/tuna/tinyAgent/tinyagent/core/adapters.py`

```python
def get_adapter(model: str, tools: list[Tool], mode: str) -> ToolCallingAdapter:
    """Factory for selecting appropriate adapter"""
    if mode == "native" and supports_native_tools(model):
        return NativeToolAdapter(tools)
    elif supports_structured_output(model):
        return OpenAIStructuredAdapter(tools)
    else:
        return ValidatedAdapter(OpenAIStructuredAdapter(tools))
```

**Benefits:**
- Transparent agent operation across different models
- Easy to add support for new models
- Isolated adapter testing

---

## Behavioral Patterns

### Strategy Pattern

**Location:** `/Users/tuna/tinyAgent/tinyagent/memory/manager.py`

**Purpose:** Allow configurable memory pruning strategies without modifying core logic.

### Implementation

```python
from typing import Callable

# Strategy protocol
PruneStrategy = Callable[[list[Step]], list[Step]]

# Concrete strategies
def keep_last_n_steps(n: int) -> PruneStrategy:
    def prune(steps: list[Step]) -> list[Step]:
        return steps[-n:] if len(steps) > n else steps
    return prune

def prune_old_observations(max_age: int) -> PruneStrategy:
    def prune(steps: list[Step]) -> list[Step]:
        now = time.time()
        return [
            step for step in steps
            if not (isinstance(step, ActionStep) and
                   now - step.timestamp.timestamp() > max_age)
        ]
    return prune

# Context class
class MemoryManager:
    def __init__(self, strategy: PruneStrategy | None = None):
        self._strategy = strategy or keep_last_n_steps(50)

    def prune(self) -> None:
        self._steps = self._strategy(self._steps)
```

**Usage:**

```python
# Configure with different strategies
memory = MemoryManager(strategy=keep_last_n_steps(100))
memory = MemoryManager(strategy=prune_old_observations(3600))
```

**Benefits:**
- Runtime pluggability
- Easy to add new pruning strategies
- No changes to MemoryManager core logic

---

## Creational Patterns

### Registry Pattern

**Location:** `/Users/tuna/tinyAgent/tinyagent/core/registry.py`

**Purpose:** Centralized tool registration with validation and metadata.

### Implementation

```python
# Decorator-based registration
def tool(func: Callable) -> Tool:
    # Validate: must have docstring
    if not func.__doc__:
        raise ValueError("Tools must have docstrings")

    # Validate: must have type hints
    if not get_type_hints(func):
        raise ValueError("Tools must have type hints")

    # Create tool object
    return Tool(
        name=func.__name__,
        func=func,
        schema=generate_json_schema(func),
        doc=func.__doc__
    )

# Usage
@tool
async def web_search(query: str) -> str:
    """Search the web for a query"""
    return await search_api(query)
```

**Benefits:**
- Fail-fast validation (catches errors at definition time)
- Self-documenting (docstrings become descriptions)
- Automatic schema generation
- Centralized tool management

---

## Data-Centric Patterns

### State Object Pattern

**Location:** `/Users/tuna/tinyAgent/tinyagent/memory/steps.py`

**Purpose:** Represent discrete events in agent conversation history as structured objects.

### Hierarchy

```python
@dataclass
class Step:
    timestamp: datetime
    step_number: int

    def to_messages(self) -> list[Message]:
        raise NotImplementedError
```

**Concrete State Objects:**

1. **SystemPromptStep**: Initial system prompt
   ```python
   def to_messages(self) -> list[Message]:
       return [{"role": "system", "content": self.content}]
   ```

2. **TaskStep**: User task/query
   ```python
   def to_messages(self) -> list[Message]:
       return [{"role": "user", "content": self.task}]
   ```

3. **ActionStep**: Agent action + observation
   ```python
   def to_messages(self) -> list[Message]:
       return [
           {"role": "assistant", "content": self.reasoning},
           {"role": "tool", "content": self.observation}
       ]
   ```

**Benefits:**
- Type-safe state representation
- Polymorphic message conversion
- Rich metadata (timestamps, step numbers)
- Easy to extend with new step types

---

### Finalizer Object Pattern

**Location:** `/Users/tuna/tinyAgent/tinyagent/core/finalizer.py`

**Purpose:** Ensure thread-safe, single-assignment final answer.

### Implementation

```python
class Finalizer:
    def __init__(self):
        self._lock = threading.Lock()
        self._answer: FinalAnswer | None = None

    def set_answer(self, value: Any, metadata: dict[str, Any] | None = None):
        with self._lock:
            if self._answer is not None:
                raise RuntimeError("Final answer already set")
            self._answer = FinalAnswer(value=value, metadata=metadata or {})

    @property
    def is_set(self) -> bool:
        return self._answer is not None

    @property
    def answer(self) -> FinalAnswer:
        if self._answer is None:
            raise RuntimeError("Answer not set")
        return self._answer
```

**Usage in TinyCodeAgent:**

```python
# Inject final_answer into executor namespace
def final_answer(value: Any) -> None:
    self._finalizer.set_answer(value)

# Check after execution
if self._finalizer.is_set:
    return self._finalizer.answer.value
```

**Benefits:**
- Prevents multiple final answers
- Thread-safe for concurrent execution
- Explicit completion signaling
- Rich metadata capture

---

## Architectural Patterns

### Protocol (Interface Segregation)

**Location:** `/Users/tuna/tinyAgent/tinyagent/execution/protocol.py`

**Purpose:** Define contracts between components, enabling loose coupling.

### Executor Protocol

```python
from typing import Protocol

class Executor(Protocol):
    async def run(self, code: str) -> str:
        """Execute code and return stdout"""
        ...

    async def kill(self) -> None:
        """Terminate execution"""
        ...

    def inject(self, name: str, value: Any) -> None:
        """Inject variable into execution namespace"""
        ...

    async def reset(self) -> None:
        """Reset execution state"""
        ...
```

**Benefits:**
- Concrete implementations can vary widely
- Easy to create test doubles/mocks
- No inheritance required
- Clear interface documentation

---

### Dependency Injection Pattern

**Purpose:** Provide components with their dependencies rather than creating them internally.

### Examples

1. **Tool Injection:**
   ```python
   # Agent receives tools externally
   agent = ReactAgent(
       tools=[web_search, calculator, file_reader],
       model="gpt-4"
   )
   ```

2. **Executor Injection:**
   ```python
   # Agent receives executor externally
   agent = TinyCodeAgent(
       executor=LocalExecutor(trust_level=TrustLevel.LOCAL)
   )
   ```

3. **Memory Injection:**
   ```python
   # Agent receives pre-configured memory
   memory = MemoryManager(strategy=keep_last_n_steps(100))
   agent = TinyCodeAgent(memory_manager=memory)
   ```

4. **Signal Collector Injection:**
   ```python
   # External component registers for signals
   def handle_signal(signal: Signal):
       logger.info(f"Signal: {signal.type} - {signal.message}")

   set_signal_collector(handle_signal)
   ```

**Benefits:**
- Configurable components
- Easy testing with mocks
- Loose coupling
- Flexible composition

---

## Safety Patterns

### Graduated Trust Pattern

**Location:** `/Users/tuna/tinyAgent/tinyagent/execution/local.py`

**Purpose:** Allow different security levels based on trust in code.

### Implementation

```python
class TrustLevel(Enum):
    LOCAL = "local"          # Full system access
    ISOLATED = "isolated"    # Process isolation
    SANDBOXED = "sandboxed"  # Container/jail

class LocalExecutor:
    def __init__(self, trust_level: TrustLevel):
        self._trust_level = trust_level
        self._namespace = self._build_namespace()

    def _build_namespace(self) -> dict[str, Any]:
        if self._trust_level == TrustLevel.LOCAL:
            return self._local_namespace()
        elif self._trust_level == TrustLevel.ISOLATED:
            return self._isolated_namespace()
        else:
            return self._sandboxed_namespace()
```

**Benefits:**
- Appropriate security for different contexts
- Trusted code runs faster (less overhead)
- Untrusted code runs safer (more isolation)

---

### Fail-Fast Validation Pattern

**Location:** `/Users/tuna/tinyAgent/tinyagent/core/registry.py`

**Purpose:** Catch errors at definition time rather than runtime.

### Implementation

```python
def tool(func: Callable) -> Tool:
    # Immediate validation
    _validate_function(func)

    # Fail fast with clear error
    if not func.__doc__:
        raise ToolDefinitionError(
            f"Tool '{func.__name__}' must have a docstring. "
            "This is required for LLM function descriptions."
        )

    return Tool(...)
```

**Benefits:**
- Errors caught during development
- Clear error messages
- Prevents cryptic runtime failures
- Better developer experience

---

## Cross-Cutting Patterns

### Observer Pattern (Signals)

**Location:** `/Users/tuna/tinyAgent/tinyagent/signals/`

**Purpose:** Allow code to emit cognitive signals for external observation.

### Implementation

```python
# Signal emitter
def uncertain(message: str) -> None:
    """Emit uncertainty signal"""
    _emit_signal(Signal(type="uncertain", message=message))

# Signal collector (injected)
_collector: Callable[[Signal], None] | None = None

def set_signal_collector(collector: Callable[[Signal], None]):
    global _collector
    _collector = collector

# Usage in agent code
def _emit_signal(signal: Signal):
    if _collector:
        _collector(signal)
```

**Benefits:**
- Decoupled observation
- Rich debugging information
- No performance overhead when unused
- Easy to add new signal types

---

## Pattern Catalog Summary

| Pattern | Location | Purpose |
|---------|----------|---------|
| ReAct | `agents/` | Reasoning + action loop |
| Adapter | `core/adapters.py` | Model compatibility |
| Strategy | `memory/manager.py` | Pluggable pruning |
| Registry | `core/registry.py` | Tool registration |
| State Object | `memory/steps.py` | Structured history |
| Finalizer | `core/finalizer.py` | Single-assignment answer |
| Protocol | `execution/protocol.py` | Interface contracts |
| Dependency Injection | Throughout | Loose coupling |
| Graduated Trust | `execution/local.py` | Security levels |
| Fail-Fast | `core/registry.py` | Early validation |
| Observer | `signals/` | Cognitive signals |

---

## Related Documentation

- **Agent Hierarchy**: `/docs/architecture/agent-hierarchy.md`
- **Tool Calling**: `/docs/architecture/tools/tool-calling-adapters.md`
- **Memory Management**: `/docs/architecture/memory-management.md`
- **Code Execution**: `/docs/architecture/code-execution.md`
