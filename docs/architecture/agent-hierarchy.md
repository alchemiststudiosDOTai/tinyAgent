---
title: Agent Hierarchy
path: agents/
type: directory
depth: 1
description: Agent inheritance hierarchy and concrete implementations
seams: [A]
---

# Agent Hierarchy

## Overview

The tinyAgent framework employs a shallow but focused inheritance hierarchy for agent implementations. The design prioritizes composition over deep inheritance, using base classes primarily for shared utility logic rather than defining complex behavioral contracts.

## Class Hierarchy

```
BaseAgent (abstract)
├── ReactAgent
└── TinyCodeAgent
```

## BaseAgent

**Location:** `/Users/tuna/tinyAgent/tinyagent/agents/base.py`

### Purpose

`BaseAgent` is an abstract base class that eliminates code duplication between concrete agent implementations. It provides shared infrastructure for tool management but does not define the core agent execution loop.

### Key Responsibilities

1. **Tool Validation**: Ensures all provided items are valid `Tool` objects
2. **Tool Registry**: Builds and maintains `_tool_map`, a name-to-tool mapping for efficient lookups
3. **Initialization Contract**: Establishes common initialization parameters for all agents

### Design Decision

The framework intentionally keeps `BaseAgent` minimal rather than defining an abstract `run()` method. This allows concrete agent implementations (`ReactAgent`, `TinyCodeAgent`) to have fundamentally different execution models:
- `ReactAgent`: JSON-based tool calling with ReAct loop
- `TinyCodeAgent`: Python code generation and execution

### Code Pattern

```python
class BaseAgent:
    def __init__(self, tools: list[Any]):
        # Validate all items are Tool objects
        # Build name-to-tool mapping
        self._tool_map: dict[str, Tool] = {
            tool.name: tool for tool in tools
        }
```

---

## ReactAgent

**Location:** `/Users/tuna/tinyAgent/tinyagent/agents/react.py`

### Architecture Pattern

Implements the **ReAct (Reason+Act)** pattern for tool-based agents using JSON-structured tool calling.

### Core Loop

1. **Reason**: LLM generates thoughts in a scratchpad format
2. **Act**: Choose to either:
   - Call a tool (returns JSON `{"tool": "name", "arguments": {...}}`)
   - Provide final answer (returns JSON `{"answer": "..."}`)

### Memory System

Uses `core.memory.Memory` - a simple list-based storage for chronological message history:
- System prompt
- User tasks
- Assistant messages (with tool calls)
- Tool result messages

### Tool Calling Architecture

Employs the **Adapter Pattern** via `ToolCallingAdapter` protocol:

```python
# Adapter selection based on model capabilities
adapter = get_adapter(
    model=self.model,
    tools=self.tools,
    mode=tool_calling_mode  # "auto", "native", "structured"
)
```

**Adapter Types:**
- `NativeToolAdapter`: For models with native function calling (GPT-4, Claude)
- `OpenAIStructuredAdapter`: For models supporting structured JSON output
- `ValidatedAdapter`: Wraps any adapter with Pydantic validation

### Data Flow

```
User Task → Memory → LLM Request (with tools) →
LLM Response → Adapter Extracts Tool Call →
Tool Execution → Result Added to Memory → Loop
```

### Key Features

- **Fail-fast validation**: Tools validated at definition time
- **Flexible tool calling**: Adapters transparently handle model differences
- **Structured memory**: Full conversation history maintained for context

---

## TinyCodeAgent

**Location:** `/Users/tuna/tinyAgent/tinyagent/agents/code.py`

### Architecture Pattern

Adapts the **ReAct pattern** to a code-centric workflow where:
- **Reason**: LLM writes Python code with embedded comments
- **Act**: Always generates and executes a Python code block

### Core Innovation

Instead of calling tools via JSON, the LLM writes Python code that:
1. Imports/calls available tool functions directly
2. Uses cognitive signals (`commit()`, `explore()`, `uncertain()`)
3. Manipulates a scratchpad memory via `store()`, `recall()`, `observe()`
4. Signals completion via `final_answer()`

### Memory Systems

Uses **two-tier memory architecture**:

1. **MemoryManager**: Structured conversation log
   - Holds `Step` objects (`SystemPromptStep`, `TaskStep`, `ActionStep`)
   - Provides long-term context for LLM
   - Supports intelligent pruning strategies

2. **AgentMemory Scratchpad**: Working memory
   - Key-value store for variables (`store`/`recall`)
   - Observation logging (`observe`)
   - Failed attempt tracking (`fail`)
   - Injected directly into executor namespace

### Execution Architecture

**Separation of Concerns**: The agent delegates code execution to an `Executor` protocol, enabling:
- **Graduated Trust**: Different trust levels (`LOCAL`, `ISOLATED`, `SANDBOXED`)
- **Security**: Sandboxing for untrusted code
- **Flexibility**: Swappable execution backends

```python
# Protocol-based execution
executor: Executor = LocalExecutor(
    trust_level=TrustLevel.LOCAL,
    limits=ExecutionLimits(timeout=30)
)
```

### Sandbox Design

`LocalExecutor` creates a restricted namespace:
- Curated safe built-ins
- Custom `__import__` with module whitelist
- AST-based security checking before execution
- Captured stdout as output

### Signaling System

Cognitive signals injected into executor namespace:
- `uncertain(message)`: Agent expresses doubt
- `explore(topic)`: Agent indicates exploratory phase
- `commit(result)`: Agent commits to a line of reasoning
- `final_answer(value)`: Signals completion

Collected via dependency injection pattern for observability.

### Data Flow

```
User Task → MemoryManager → LLM Request →
Python Code Generation → AST Validation →
Executor.run(code) → Namespace Execution →
stdout + Scratchpad Context → Memory Update → Loop
```

### Key Features

- **Safety-first**: AST validation and namespace isolation
- **Observability**: Cognitive signals for debugging
- **Memory efficiency**: Intelligent context pruning
- **Rich working memory**: Scratchpad for stateful reasoning

---

## Architectural Trade-offs

### Composition Over Inheritance

Both agents inherit from `BaseAgent` for shared tool management, but implement entirely different `run()` methods. This avoids:
- Fragile base class problem
- Complex inheritance hierarchies
- Behavioral coupling between agent types

### Protocol-Based Design

The `Executor` protocol allows `TinyCodeAgent` to be decoupled from execution details:
- No knowledge of `exec()` vs. Docker vs. remote execution
- Easy testing with mock executors
- Future-proof for new execution backends

### Memory Strategy Divergence

- `ReactAgent`: Simple chronological message list
- `TinyCodeAgent`: Structured `Step` objects with pruning

This reflects the different needs of the agents:
- JSON tool calls need full history for context
- Code execution benefits from structured, prunable memory

---

## Extension Points

### Creating New Agents

1. Inherit from `BaseAgent` for tool management
2. Implement `async def run()` method
3. Choose memory strategy:
   - Simple list-based (`core.memory.Memory`)
   - Structured (`memory.manager.MemoryManager`)
4. Define execution pattern:
   - Tool calling via adapters
   - Code generation via `Executor`
   - Custom hybrid approach

### Example Skeleton

```python
from agents.base import BaseAgent
from core.types import RunResult

class CustomAgent(BaseAgent):
    async def run(self, task: str) -> RunResult:
        # Initialize memory
        # Implement reasoning loop
        # Execute actions (tools, code, or custom)
        # Return RunResult
        pass
```

---

## Related Documentation

- **Tool Calling**: `/docs/architecture/tool-calling-architecture.md`
- **Memory Management**: `/docs/architecture/memory-management.md`
- **Code Execution**: `/docs/architecture/code-execution.md`
- **Adapters**: `/docs/architecture/tools/tool-calling-adapters.md`
