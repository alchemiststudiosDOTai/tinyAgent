---
title: tinyAgent Module Documentation
path: docs/modules/
type: index
depth: 0
description: Comprehensive index of all tinyAgent framework modules
exports: []
seams: []
---

# tinyAgent Module Documentation

This directory contains comprehensive documentation for all key modules in the tinyAgent framework. Each module is documented with its location, purpose, implementation details, design rationale, and architectural integration.

## Documentation Index

### Agent Modules

| Module | Description |
|--------|-------------|
| [agents/base.md](agents_base.md) | Abstract base class providing tool management infrastructure for all agent types |
| [agents/react.md](agents_react.md) | ReAct (Reason + Act) pattern agent for JSON-tool calling with iterative reasoning loop |
| [agents/code.md](agents_code.md) | Python-executing ReAct agent with sandboxed execution and graduated trust levels |

### Core Modules

| Module | Description |
|--------|-------------|
| [core/adapters.md](core_adapters.md) | LLM tool calling abstraction layer with multi-format support |
| [core/schema.md](core_schema.md) | Python type hints to JSON Schema conversion for tool argument definition |
| [core/parsing.md](core_parsing.md) | Robust JSON parsing for LLM responses with wrapper handling |
| [core/types.md](core_types.md) | Fundamental data structures for agent answers and execution results |
| [core/exceptions.md](core_exceptions.md) | Specialized exceptions for agent execution and final answer validation |
| [core/finalizer.md](core_finalizer.md) | Thread-safe singleton for managing agent final answers |
| [core/registry.md](core_registry.md) | Tool decorator and wrapper for validated, async-aware function registration |

### Execution Modules

| Module | Description |
|--------|-------------|
| [execution/protocol.md](execution_protocol.md) | Standard interface and result structure for code execution backends |
| [execution/local.md](execution_local.md) | Sandboxed Python code execution in restricted process environment |

### Memory Modules

| Module | Description |
|--------|-------------|
| [memory/manager.md](memory_manager.md) | Conversation history management with pruning strategies for LLM context optimization |

### Prompt Modules

| Module | Description |
|--------|-------------|
| [prompts/templates.md](prompts_templates.md) | Core prompt templates defining agent behavior and interaction formats |
| [prompts/loader.md](prompts_loader.md) | Dynamic prompt loading from files with fallback mechanism |

### Tool Modules

| Module | Description |
|--------|-------------|
| [tools/builtin.md](tools_builtin.md) | Standard tool implementations for planning, web browsing, and web search |
| [tools/validation.md](tools_validation.md) | Static analysis validation for tool class structure and serialization safety |

### Signal Modules

| Module | Description |
|--------|-------------|
| [signals.md](signals.md) | LLM cognitive state communication primitives for transparency and observability |

### Limit Modules

| Module | Description |
|--------|-------------|
| [limits.md](limits.md) | Resource boundary and timeout management for code execution |

## Architecture Overview

The tinyAgent framework is organized into distinct layers:

1. **Agent Layer** (`agents/`): Concrete agent implementations using different execution patterns
2. **Core Layer** (`core/`): Fundamental abstractions for tools, types, execution, and error handling
3. **Execution Layer** (`execution/`): Code execution backends with protocol definitions
4. **Memory Layer** (`memory/`): Conversation and context management
5. **Prompt Layer** (`prompts/`): Behavior definition and template management
6. **Tool Layer** (`tools/`): Extensible tool ecosystem with validation

## Key Design Patterns

- **Adapter Pattern**: LLM tool calling abstraction
- **Protocol Pattern**: Execution backend interface
- **Decorator Pattern**: Tool registration and validation
- **Strategy Pattern**: Memory pruning strategies
- **Singleton Pattern**: Final answer management

## Module Dependencies

```
agents/
    ├── base (foundation for all agents)
    ├── react (uses: adapters, memory, prompts)
    └── code (uses: execution, memory, signals, limits)

core/
    ├── adapters (uses: registry, schema)
    ├── schema (uses: registry)
    ├── registry (foundational - no dependencies)
    ├── types (foundational - no dependencies)
    ├── exceptions (uses: types)
    ├── finalizer (uses: types, exceptions)
    └── parsing (standalone utility)

execution/
    ├── protocol (foundational interface)
    └── local (uses: protocol, limits)

memory/
    └── manager (uses: steps types)

prompts/
    ├── templates (foundational constants)
    └── loader (standalone utility)

tools/
    ├── builtin/ (uses: registry decorator)
    └── validation (standalone AST analysis)

signals/ (standalone primitives)
limits/ (used by: execution, agents)
```

## Usage

Each module documentation file includes:

- **Where**: File location in the codebase
- **What**: Purpose and responsibility
- **How**: Key implementation details
- **Why**: Design rationale and architectural role

Files use frontmatter with metadata including:
- `title`: Human-readable module name
- `path`: Relative path from project root
- `type`: File or directory
- `depth`: Nesting level in architecture
- `description`: One-line summary
- `exports`: List of key public exports
- `seams`: Modularity markers (M = module boundary)
