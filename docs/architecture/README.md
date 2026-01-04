---
title: Architecture Documentation Index
path: docs/architecture/
type: directory
depth: 2
description: Complete index of tinyAgent architecture documentation
seams: [A]
---

# tinyAgent Architecture Documentation

## Overview

This directory contains comprehensive architecture documentation for the tinyAgent framework. These documents analyze the design patterns, data flow, dependencies, and module relationships that make up the framework.

## Documentation Files

### Core Architecture Documents

#### [Agent Hierarchy](./agent-hierarchy.md)
**Purpose:** Documents the inheritance hierarchy and concrete agent implementations

**Contents:**
- `BaseAgent` abstract base class
- `ReactAgent` (JSON tool-calling)
- `TinyCodeAgent` (Python code execution)
- Architectural trade-offs and extension points

**Key Topics:**
- ReAct pattern implementations
- Memory system differences
- Tool calling vs. code generation
- Protocol-based execution design

**Seams:** Agent initialization, tool management, execution loops

---

#### [Design Patterns](./design-patterns.md)
**Purpose:** Catalog of architectural and design patterns used throughout the framework

**Contents:**
- Agent patterns (ReAct)
- Structural patterns (Adapter, Strategy, Registry)
- Behavioral patterns (Observer, Dependency Injection)
- Safety patterns (Graduated Trust, Fail-Fast)

**Key Topics:**
- Tool calling adapter architecture
- Memory pruning strategies
- Tool registration pattern
- Finalizer object pattern
- Signal-based observation

**Seams:** Protocol definitions, strategy injection, adapter selection

---

#### [Data Flow Architecture](./data-flow.md)
**Purpose:** Complete trace of data transformation from user request to final output

**Contents:**
- Input phase and initialization
- ReAct loop execution
- Response processing
- Tool/code execution
- Memory updates
- Output construction

**Key Topics:**
- ReactAgent data flow
- TinyCodeAgent data flow
- Memory transformation examples
- Error handling flow
- Performance considerations

**Seams:** LLM API boundaries, execution interfaces, memory updates

---

#### [Dependencies and Module Relationships](./dependencies.md)
**Purpose:** External dependencies and internal module coupling analysis

**Contents:**
- External library dependencies
- Internal module structure
- Dependency rules and prevention
- Interface boundaries
- Dependency injection patterns

**Key Topics:**
- Core dependencies (openai, pydantic, python-dotenv)
- Optional dependencies (httpx, markdownify)
- Layered architecture
- Protocol-based interfaces
- Circular dependency prevention

**Seams:** Module boundaries, protocol definitions, injection points

---

#### [Memory Management Architecture](./memory-management.md)
**Purpose:** Memory systems, pruning strategies, and state management

**Contents:**
- Two-tier memory architecture
- Memory Manager (long-term)
- Scratchpad Memory (working)
- Pruning strategies
- Memory lifecycle
- Token management

**Key Topics:**
- Step hierarchy (SystemPromptStep, TaskStep, ActionStep)
- Pruning strategies (keep-last-n, prune-old-observations)
- Scratchpad patterns (store/recall, observe, fail)
- Adaptive pruning
- Performance optimization

**Seams:** Memory initialization, pruning strategies, context conversion

---

#### [Tool Calling Architecture](./tool-calling-architecture.md)
**Purpose:** Tool registration, adapters, and execution patterns

**Contents:**
- Tool registry and `@tool` decorator
- Schema generation
- Tool calling adapters
- Adapter factory pattern
- Tool execution
- Tool validation

**Key Topics:**
- NativeToolAdapter (GPT-4, Claude)
- OpenAIStructuredAdapter (JSON mode)
- ValidatedAdapter (Pydantic validation)
- Async/sync handling
- Tool patterns

**Seams:** Tool registration, adapter selection, execution interface

---

## Architecture Overview

### Design Philosophy

The tinyAgent framework is built on these core principles:

1. **Separation of Concerns:** Each module has a single, well-defined responsibility
2. **Composition Over Inheritance:** Prefer composition and protocols to deep inheritance hierarchies
3. **Fail-Fast Validation:** Catch errors at definition time, not runtime
4. **Graduated Trust:** Support multiple security levels for code execution
5. **Adapter Pattern:** Transparent support for different LLM capabilities

### Layered Architecture

```
┌────────────────────────────────────────┐
│           Application Layer            │  ← Your code
├────────────────────────────────────────┤
│            Agent Layer                 │  ← agents/
│  (ReactAgent, TinyCodeAgent)           │
├────────────────────────────────────────┤
│           Abstraction Layer            │  ← core/
│  (Tools, Adapters, Types, Protocols)   │
├────────────────────────────────────────┤
│         Implementation Layers          │
│  (execution/, memory/, signals/, etc)  │
└────────────────────────────────────────┘
```

### Key Architectural Decisions

#### 1. Protocol-Based Design

**Rationale:** Enables loose coupling and easy testing

**Example:**
```python
# Protocol definition
class Executor(Protocol):
    async def run(self, code: str) -> str: ...

# Any implementation works
executor: Executor = LocalExecutor(...)
executor: Executor = DockerExecutor(...)
```

#### 2. Adapter Pattern for Tool Calling

**Rationale:** Different LLMs have different tool-calling mechanisms

**Example:**
```python
# Same agent, different models
agent = ReactAgent(model="gpt-4")      # Native tools
agent = ReactAgent(model="mistral")    # Structured JSON
agent = ReactAgent(model="llama-2")    # Manual parsing
```

#### 3. Two-Tier Memory

**Rationale:** Separate long-term conversation history from working memory

**Example:**
```python
# Long-term: Structured conversation log
memory_manager = MemoryManager()

# Working: Transient state during execution
scratchpad = AgentMemory()
```

#### 4. Fail-Fast Validation

**Rationale:** Catch errors early with clear messages

**Example:**
```python
@tool
def my_tool():  # Error: Missing docstring
    pass

# Caught at import time, not during agent execution
```

---

## System Seams (Extension Points)

### Agent Seams

- **Tool Registration:** Add new tools via `@tool` decorator
- **Executor Injection:** Provide custom execution backends
- **Memory Strategy:** Configure pruning strategies
- **Prompt Templates:** Override system prompts

### Core Seams

- **Adapter Implementation:** Support new model tool-calling formats
- **Validation:** Add custom validation logic
- **Type Conversion:** Extend JSON schema generation

### Execution Seams

- **Executor Protocol:** Implement new execution backends
- **Trust Levels:** Add new security levels
- **Resource Limits:** Configure timeouts and quotas

### Memory Seams

- **Step Types:** Add new step types
- **Pruning Strategies:** Implement custom pruning logic
- **Storage Backends:** Persist memory to databases

---

## Reading Guide

### For Framework Users

Start with:
1. **Agent Hierarchy** - Understand available agents
2. **Tool Calling Architecture** - Learn to create tools
3. **Memory Management** - Configure memory strategies

### For Contributors

Start with:
1. **Design Patterns** - Understand architectural patterns
2. **Dependencies** - Learn module structure
3. **Data Flow** - Trace execution flow

### For Architecture Review

Start with:
1. **Design Patterns** - High-level patterns
2. **Dependencies** - Module relationships
3. **Data Flow** - End-to-end flow

### For Debugging

Start with:
1. **Data Flow** - Trace execution
2. **Memory Management** - Inspect state
3. **Tool Calling** - Tool execution issues

---

## Architecture Diagrams

### Component Relationship Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      Application                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                        Agents                           │
│  ┌──────────────┐           ┌──────────────┐           │
│  │ ReactAgent   │           │TinyCodeAgent │           │
│  │ (JSON tools) │           │ (Code exec)  │           │
│  └──────┬───────┘           └──────┬───────┘           │
└─────────┼──────────────────────────┼────────────────────┘
          │                          │
          ▼                          ▼
┌─────────────────────────────────────────────────────────┐
│                         Core                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Registry │  │ Adapters │  │  Types   │             │
│  │  (@tool) │  │ (Models) │  │(Result)  │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Execution   │ │   Memory     │ │   Signals    │
│ (LocalExec)  │ │ (Manager)    │ │(Observability)│
└──────────────┘ └──────────────┘ └──────────────┘
```

### Data Flow Diagram

```
User Request
      │
      ▼
┌─────────────┐
│ Initialization│
│ - Memory     │
│ - Tools      │
│ - Executor   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ ReAct Loop  │◄────────┐
└──────┬──────┘         │
       │                │
       ▼                │
┌─────────────┐         │
│ LLM Request │         │
│ + Tools     │         │
└──────┬──────┘         │
       │                │
       ▼                │
┌─────────────┐         │
│ LLM Response│         │
└──────┬──────┘         │
       │                │
       ├────────────────┤
       │                │
       ▼                ▼
┌──────────┐    ┌────────────┐
│Tool Call │    │Final Answer│
└────┬─────┘    └────┬───────┘
     │              │
     ▼              │
┌──────────┐        │
│Execution │        │
└────┬─────┘        │
     │              │
     ▼              │
┌──────────┐        │
│Observation│       │
└────┬─────┘        │
     │              │
     └──────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ Memory Update │
    └───────────────┘
```

---

## Contributing to Architecture Documentation

### Adding New Documents

1. Use required frontmatter:
   ```yaml
   ---
   title: Human-readable name
   path: relative/path/from/root
   type: directory
   depth: 0-N
   description: One-line purpose summary
   seams: [A]
   ---
   ```

2. Place in `/Users/tuna/tinyAgent/tinyagent/docs/architecture/`

3. Update this index

### Documentation Standards

- **Absolute paths only:** No relative paths
- **Code examples:** Show actual usage patterns
- **Diagrams:** Use ASCII art for compatibility
- **Cross-references:** Link to related documents
- **Seams section:** Document extension points

---

## Related Documentation

### External Documentation

- **API Reference:** `/docs/api/`
- **User Guide:** `/docs/guide/`
- **Examples:** `/examples/`
- **Tests:** `/tests/`

### Internal Documentation

- **Source Code:** `/Users/tuna/tinyAgent/tinyagent/`
- **Type Hints:** Throughout codebase
- **Docstrings:** All public APIs

---

## Quick Reference

### File Locations

| Component | Path |
|-----------|------|
| Agents | `/Users/tuna/tinyAgent/tinyagent/agents/` |
| Core | `/Users/tuna/tinyAgent/tinyagent/core/` |
| Execution | `/Users/tuna/tinyAgent/tinyagent/execution/` |
| Memory | `/Users/tuna/tinyAgent/tinyagent/memory/` |
| Signals | `/Users/tuna/tinyAgent/tinyagent/signals/` |
| Tools | `/Users/tuna/tinyAgent/tinyagent/tools/` |
| Limits | `/Users/tuna/tinyAgent/tinyagent/limits/` |
| Prompts | `/Users/tuna/tinyAgent/tinyagent/prompts/` |

### Key Protocols

| Protocol | Location | Purpose |
|----------|----------|---------|
| `Executor` | `execution/protocol.py` | Code execution backends |
| `ToolCallingAdapter` | `core/adapters.py` | Model tool-calling formats |
| `PruneStrategy` | `memory/manager.py` | Memory pruning strategies |

### Key Classes

| Class | Location | Purpose |
|-------|----------|---------|
| `BaseAgent` | `agents/base.py` | Shared agent logic |
| `ReactAgent` | `agents/react.py` | JSON tool-calling agent |
| `TinyCodeAgent` | `agents/code.py` | Code execution agent |
| `Tool` | `core/registry.py` | Tool representation |
| `MemoryManager` | `memory/manager.py` | Structured memory |
| `Finalizer` | `core/finalizer.py` | Final answer management |

---

**Last Updated:** 2026-01-03
**Framework Version:** 0.1.0
**Documentation Status:** Complete
