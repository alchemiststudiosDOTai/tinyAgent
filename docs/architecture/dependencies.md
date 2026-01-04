---
title: Dependencies and Module Relationships
path: architecture/
type: directory
depth: 0
description: External dependencies and internal module coupling
seams: [A]
---

# Dependencies and Module Relationships

## Overview

This document catalogs the tinyAgent framework's dependencies—both external libraries and internal module relationships—and explains their purposes and coupling patterns.

---

## External Dependencies

### Core Dependencies

#### `openai`

**Version:** Latest
**Purpose:** LLM API client for agent reasoning

**Usage:**
- Async chat completions API
- Tool/function calling
- Structured output mode
- Stream processing

**Key Files:**
- `agents/react.py`: Chat completions for ReAct loop
- `agents/code.py`: Code generation requests
- `core/adapters.py`: Model-specific API features

**Why Async?**
```python
# Allows concurrent tool execution
results = await asyncio.gather(*[
    tool.run(**args) for tool in tools
])
```

---

#### `pydantic`

**Version:** Latest (v2)
**Purpose:** Data validation and settings management

**Usage:**

1. **Tool Schema Generation:**
   ```python
   # core/registry.py
   class Tool(BaseModel):
       name: str
       func: Callable
       schema: dict[str, Any]  # JSON Schema
       doc: str
   ```

2. **Tool Call Validation:**
   ```python
   # core/adapters.py
   def validate_arguments(call: ToolCall, tool: Tool):
       model = create_model_from_schema(tool.schema)
       validated = model(**call.arguments)
       return validated.dict()
   ```

3. **Type Definitions:**
   ```python
   # core/types.py
   class RunResult(BaseModel):
       output: str
       final_answer: FinalAnswer
       state: Literal["completed", "step_limit_reached"]
       steps_taken: int
       duration_seconds: float
   ```

**Why Pydantic?**
- Runtime type safety
- Automatic JSON Schema generation
- Clear validation errors
- IDE support via type hints

---

#### `python-dotenv`

**Version:** Latest
**Purpose:** Environment variable management

**Usage:**
```python
# __init__.py
from dotenv import load_dotenv
load_dotenv()  # Loads .env file

# Usage
api_key = os.getenv("OPENAI_API_KEY")
```

**Configuration:**
```bash
# .env
OPENAI_API_KEY=sk-...
BRAVE_SEARCH_API_KEY=bs-...
MODEL_NAME=gpt-4
```

**Why Dotenv?**
- No hardcoded secrets
- Development/production parity
- Easy configuration management
- Git-friendly (exclude .env)

---

### Optional Dependencies

#### `httpx`

**Version:** Latest
**Purpose:** Async HTTP client for web tools

**Usage:**
```python
# tools/web.py
import httpx

async def web_search(query: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query}
        )
        return response.json()
```

**Why httpx over requests?**
- Native async support
- HTTP/2 support
- Connection pooling
- Better performance

---

#### `markdownify`

**Version:** Latest
**Purpose:** HTML to Markdown conversion

**Usage:**
```python
# tools/web.py
from markdownify import markdownify

@tool
async def web_browse(url: str) -> str:
    html = await fetch_html(url)
    markdown = markdownify(html)
    return markdown  # LLM-friendly format
```

**Why Optional?**
- Not all agents need web browsing
- Reduces core dependency footprint
- Imported within tool function to avoid hard requirement

---

## Internal Module Structure

### Layered Architecture

```
┌─────────────────────────────────────┐
│          agents/                    │  ← High-level logic
│  (ReactAgent, TinyCodeAgent)        │
└──────────┬──────────────────────────┘
           │
           ├──→ core/          ← Core abstractions
           ├──→ memory/        ← State management
           ├──→ execution/     ← Code execution
           ├──→ prompts/       ← Prompt templates
           └──→ signals/       ← Cognitive signals
```

### Dependency Rules

1. **Downward dependency flow only**
2. **No circular dependencies**
3. **Core depends on nothing**
4. **Agents depend on core**

---

## Module-by-Module Breakdown

### `agents/` (High-Level Layer)

**Location:** `/Users/tuna/tinyAgent/tinyagent/agents/`

**Dependencies:**
```python
from agents.base import BaseAgent
from core.types import RunResult, FinalAnswer
from core.registry import Tool
from core.adapters import get_adapter
from core.finalizer import Finalizer
from memory.manager import MemoryManager
from memory.scratchpad import AgentMemory
from execution.protocol import Executor
from execution.local import LocalExecutor
from prompts.loader import load_prompt
from signals.primitives import set_signal_collector
```

**Coupling:**
- **Tight:** `BaseAgent` (inheritance), `Tool` (composition)
- **Medium:** `Executor` protocol, `MemoryManager`
- **Loose:** `load_prompt` (function), `signals` (global setter)

**Files:**
- `base.py`: Base class with shared tool logic
- `react.py`: JSON tool-calling agent
- `code.py`: Code execution agent

**Depended By:**
- External applications
- Tests
- Examples

---

### `core/` (Abstraction Layer)

**Location:** `/Users/tuna/tinyAgent/tinyagent/core/`

**Dependencies:**
```python
# Minimal external dependencies
import asyncio
from typing import Protocol, Callable
from pydantic import BaseModel
```

**Internal Dependencies:**
- `core` modules depend on each other
- No dependencies on `agents`, `execution`, `memory`

**Files:**

#### `registry.py`
```python
# Tool definition and registration
# Exports: Tool, tool decorator
```

#### `adapters.py`
```python
# Tool calling adapters
# Dependencies: core.schema, core.registry
```

#### `schema.py`
```python
# JSON Schema generation
# Dependencies: core.registry
```

#### `types.py`
```python
# Core data structures
# No internal dependencies
```

#### `finalizer.py`
```python
# Final answer management
# No internal dependencies
```

**Depended By:**
- `agents/` (primary consumer)
- `tests/`
- `examples/`

---

### `execution/` (Execution Layer)

**Location:** `/Users/tuna/tinyAgent/tinyagent/execution/`

**Dependencies:**
```python
from limits.boundaries import ExecutionLimits
from signals.primitives import Signal, emit_signal
```

**Files:**

#### `protocol.py`
```python
# Executor interface
# No dependencies (protocol definition)
```

#### `local.py`
```python
# Local execution implementation
# Dependencies: execution.protocol, limits
```

**Coupling:**
- **Loose:** Protocol-based, not inheritance
- Testable with mock executors

**Depended By:**
- `agents/code.py` (TinyCodeAgent)

---

### `memory/` (State Management Layer)

**Location:** `/Users/tuna/tinyAgent/tinyagent/memory/`

**Dependencies:**
```python
from core.types import FinalAnswer
```

**Files:**

#### `manager.py`
```python
# Structured memory with Step objects
# Dependencies: memory.steps
```

#### `scratchpad.py`
```python
# Working memory for TinyCodeAgent
# No dependencies
```

#### `steps.py`
```python
# Step class hierarchy
# No dependencies
```

**Coupling:**
- **Medium:** Both agents use memory, but differently
- ReactAgent: Simple list-based (deprecated?)
- TinyCodeAgent: Structured Step-based

**Depended By:**
- `agents/react.py`
- `agents/code.py`

---

### `prompts/` (Prompt Layer)

**Location:** `/Users/tuna/tinyAgent/tinyagent/prompts/`

**Dependencies:**
```python
# No internal dependencies
```

**Files:**
- `loader.py`: Load prompts from templates
- `react_system.txt`: ReAct agent system prompt
- `code_system.txt`: Code agent system prompt

**Coupling:**
- **Very loose:** Function-based interface
- Easy to swap prompt sources

**Depended By:**
- `agents/react.py`
- `agents/code.py`

---

### `signals/` (Observability Layer)

**Location:** `/Users/tuna/tinyAgent/tinyagent/signals/`

**Dependencies:**
```python
# No internal dependencies
```

**Files:**
- `primitives.py`: Signal emission and collection
- `types.py`: Signal data structures

**Coupling:**
- **Very loose:** Global setter pattern
- Optional (no performance cost if unused)

**Depended By:**
- `agents/code.py` (emitter)
- External consumers (collectors)

---

### `limits/` (Resource Management Layer)

**Location:** `/Users/tuna/tinyAgent/tinyagent/limits/`

**Dependencies:**
```python
# No internal dependencies
```

**Files:**
- `boundaries.py`: Execution limits (timeout, output truncation)
- `context.py`: Timeout context manager

**Coupling:**
- **Loose:** Context manager interface

**Depended By:**
- `execution/local.py`
- `tools/` (for external API limits)

---

### `tools/` (Tool Library)

**Location:** `/Users/tuna/tinyAgent/tinyagent/tools/`

**Dependencies:**
```python
from core.registry import tool
import httpx  # Optional
from markdownify import markdownify as md  # Optional
```

**Files:**
- `web.py`: web_search, web_browse
- `planning.py`: Planning tools
- `validation.py`: Tool validation utilities

**Coupling:**
- **Very loose:** Only depends on `@tool` decorator
- Tools are independent functions

**Depended By:**
- Agent instantiation (passed as tools list)

---

## Dependency Graph

### Visual Representation

```
                    ┌─────────────┐
                    │  External   │
                    │  Libraries  │
                    └──────┬──────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│                      core/                           │
│  (registry, adapters, types, finalizer, schema)     │
└──────────────────────────┬──────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  execution/  │  │   memory/    │  │   signals/   │
└──────────────┘  └──────────────┘  └──────────────┘
         │                 │
         └─────────┬───────┘
                   │
                   ▼
         ┌───────────────────┐
         │     agents/       │
         │ (ReactAgent,      │
         │  TinyCodeAgent)   │
         └─────────┬─────────┘
                   │
                   ▼
         ┌───────────────────┐
         │   Application     │
         └───────────────────┘
```

### Key Observations

1. **Core is foundation**: Everything depends on `core/`
2. **Execution is isolated**: Only used by TinyCodeAgent
3. **Memory is shared**: Both agents use memory differently
4. **Signals are optional**: Loose coupling via global setter
5. **Agents are integration point**: Combine all modules

---

## Interface Boundaries

### Protocols (Interfaces)

#### `Executor` Protocol

**Location:** `execution/protocol.py`

**Contract:**
```python
class Executor(Protocol):
    async def run(self, code: str) -> str: ...
    async def kill(self) -> None: ...
    def inject(self, name: str, value: Any) -> None: ...
    async def reset(self) -> None: ...
```

**Implementations:**
- `LocalExecutor` (current)
- `DockerExecutor` (potential)
- `RemoteExecutor` (potential)

**Benefits:**
- TinyCodeAgent decoupled from execution details
- Easy to test with mocks
- Future-proof for new backends

---

#### `ToolCallingAdapter` Protocol

**Location:** `core/adapters.py`

**Contract:**
```python
class ToolCallingAdapter(Protocol):
    async def format_request(self, tools: list[Tool]) -> dict: ...
    async def extract_tool_call(self, response: Any) -> ToolCall | None: ...
```

**Implementations:**
- `NativeToolAdapter` (GPT-4, Claude)
- `OpenAIStructuredAdapter` (JSON mode)
- `ValidatedAdapter` (with Pydantic)

**Benefits:**
- ReactAgent decoupled from model differences
- Easy to add new model support
- Consistent interface

---

### Abstract Base Classes

#### `BaseAgent`

**Location:** `agents/base.py`

**Contract:**
```python
class BaseAgent(ABC):
    def __init__(self, tools: list[Any]):
        # Validate tools
        # Build tool map
        ...

    @abstractmethod
    async def run(self, task: str) -> RunResult:
        ...
```

**Benefits:**
- Shared tool management
- Consistent initialization
- Type safety for tools

---

## Dependency Injection Patterns

### Constructor Injection

```python
# Tools injected at creation
agent = ReactAgent(
    tools=[search_tool, calculator],  # ← Injected
    model="gpt-4"
)

# Executor injected at creation
agent = TinyCodeAgent(
    executor=LocalExecutor(...),  # ← Injected
    model="gpt-4"
)
```

### Function Injection

```python
# Signal collector injected via setter
def my_collector(signal: Signal):
    print(f"Signal: {signal}")

set_signal_collector(my_collector)  # ← Injected
```

### Namespace Injection

```python
# Tools/functions injected into executor namespace
executor.inject("web_search", search_tool.func)  # ← Injected
executor.inject("final_answer", final_answer_func)  # ← Injected
```

---

## Circular Dependency Prevention

### Current Status

**No circular dependencies exist.**

### Verification

```python
# Check for circular imports
import sys
sys.path.append("/Users/tuna/tinyAgent/tinyagent")

# Would fail if circular dependencies existed
from agents.react import ReactAgent
from execution.local import LocalExecutor
from memory.manager import MemoryManager
```

### Prevention Strategies

1. **Protocol-based design**: No implementation dependencies
2. **Layered architecture**: Downward-only dependency flow
3. **Dependency injection**: Runtime wiring, not compile-time
4. **Module boundaries**: Clear separation of concerns

---

## Dependency Management Best Practices

### Adding New Dependencies

1. **Evaluate necessity:**
   ```bash
   # Check if existing dependency can do it
   uv pip list | grep -i "http"
   ```

2. **Pin version:**
   ```bash
   # Add specific version
   uv add "package==1.2.3"
   ```

3. **Update pyproject.toml:**
   ```toml
   [project.dependencies]
   package = ">=1.0,<2.0"
   ```

4. **Document purpose:**
   ```python
   # core/registry.py
   """
   Uses Pydantic for runtime validation.
   Required for tool schema generation.
   """
   ```

### Removing Dead Dependencies

1. **Identify unused:**
   ```bash
   # Search for imports
   grep -r "import library" .
   ```

2. **Verify safe to remove:**
   ```bash
   # Run tests
   uv run pytest
   ```

3. **Remove from pyproject.toml:**
   ```bash
   uv remove library
   ```

---

## Testing Dependencies

### Test-Specific Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-mock>=3.10",
    "coverage>=7.0",
]
```

### Mock Dependencies

```python
# Test with mock executor
from unittest.mock import Mock
from execution.protocol import Executor

mock_executor = Mock(spec=Executor)
agent = TinyCodeAgent(executor=mock_executor)
```

---

## Related Documentation

- **Agent Hierarchy**: `/docs/architecture/agent-hierarchy.md`
- **Design Patterns**: `/docs/architecture/design-patterns.md`
- **Data Flow**: `/docs/architecture/data-flow.md`
- **Module Index**: `/docs/architecture/module-index.md`
