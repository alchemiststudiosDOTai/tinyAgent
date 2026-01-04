# Codebase Map

**Generated:** 2026-01-03 11:31:33 CST
**Project:** tinyAgent
**Version:** 0.1.0

---

## Statistics

| Metric | Value |
|--------|-------|
| Total Python files analyzed | 35 |
| Documentation files generated | 58 |
| Total documentation lines | 14,360 |
| Directories documented | 10 |
| Modules documented | 22 |
| Agents spawned | 6 SEAMS agents |
| Documentation depth levels | 3 |

---

## Structure Overview

### Directory Tree

```
tinyagent/
|
+-- agents/                    # [A] Agent implementations
|   |-- base.py               # BaseAgent abstract class
|   |-- react.py              # ReactAgent (JSON tool-calling)
|   |-- code.py               # TinyCodeAgent (Python execution)
|
+-- core/                      # [C] Core abstractions & utilities
|   |-- adapters.py           # Tool calling adapters
|   |-- schema.py             # JSON schema generation
|   |-- parsing.py            # JSON parsing utilities
|   |-- types.py              # Core data structures
|   |-- exceptions.py         # Custom exceptions
|   |-- finalizer.py          # Final answer manager
|   |-- registry.py           # Tool decorator (@tool)
|   |-- memory.py             # Simple memory for ReactAgent
|
+-- execution/                 # [E] Code execution subsystem
|   |-- protocol.py           # Executor protocol interface
|   |-- local.py              # Local executor implementation
|
+-- memory/                    # [M] State management
|   |-- manager.py            # MemoryManager (conversation history)
|   |-- scratchpad.py         # AgentMemory (working memory)
|   |-- steps.py              # Step type definitions
|
+-- prompts/                   # [P] Prompt templates
|   |-- loader.py             # Dynamic prompt loading
|   |-- templates.py          # System prompt constants
|
+-- signals/                   # [S] Cognitive primitives
|   |-- primitives.py         # Signal functions (commit, explore, uncertain)
|
+-- tools/                     # [T] Built-in tools
|   |-- builtin/              # Standard tool implementations
|   |   |-- planning.py       # Plan management tools
|   |   |-- web.py            # Web search and browse
|   |   |-- shell.py          # Shell command execution
|   |-- validation.py         # Tool class validator
|
+-- limits/                    # [L] Resource management
|   |-- boundaries.py         # ExecutionLimits class
```

**Legend:**
- `[A]` = Agent layer
- `[C]` = Core layer
- `[E]` = Execution layer
- `[M]` = Memory layer
- `[P]` = Prompt layer
- `[S]` = Signaling layer
- `[T]` = Tool layer
- `[L]` = Limits layer

---

## Detailed Mapping

### Structure Documentation (`docs/structure/`)

| File | Directory | Depth | Purpose | Key Exports/Seams |
|------|-----------|-------|---------|-------------------|
| `INDEX.md` | structure/ | 0 | Structure docs index | N/A |
| `agents.md` | agents/ | 1 | Agent implementations overview | BaseAgent, ReactAgent, TinyCodeAgent |
| `core.md` | core/ | 1 | Core abstractions | adapters, schema, types, registry |
| `execution.md` | execution/ | 1 | Code execution subsystem | Executor protocol, LocalExecutor |
| `limits.md` | limits/ | 1 | Resource boundaries | ExecutionLimits |
| `memory.md` | memory/ | 1 | State management | MemoryManager, AgentMemory |
| `observability.md` | observability/ | 1 | Future tracing/metrics | (Reserved) |
| `prompts.md` | prompts/ | 1 | Prompt templates | SYSTEM, CODE_SYSTEM, loader |
| `signals.md` | signals/ | 1 | Cognitive primitives | commit, explore, uncertain |
| `tools.md` | tools/ | 1 | Tool system | @tool decorator, validation |

### Entry Points Documentation (`docs/entry/`)

| File | Component | Type | Purpose | Key Exports |
|------|-----------|------|---------|-------------|
| `INDEX.md` | entry/ | index | Entry points directory index | N/A |
| `tinyagent-root.md` | tinyagent/__init__.py | package | Main package exports | All public APIs |
| `react-agent.md` | ReactAgent | class | JSON tool-calling agent | ReactAgent |
| `tinycode-agent.md` | TinyCodeAgent | class | Python code execution agent | TinyCodeAgent |
| `base-agent.md` | BaseAgent | class | Abstract base for all agents | BaseAgent |
| `tool-decorator.md` | @tool | decorator | Create tools from functions | tool |
| `tool-calling-mode.md` | ToolCallingMode | enum | Tool calling modes | AUTO, NATIVE, STRUCTURED, VALIDATED |
| `built-in-tools.md` | tools/builtin/ | module | Pre-built tools | web_search, web_browse, planning tools |
| `validation.md` | validate_tool_class | function | Static analysis for tools | validate_tool_class |
| `memory-system.md` | memory/ | package | Memory management | MemoryManager, AgentMemory |
| `signals.md` | signals/ | module | Cognitive primitives | uncertain, explore, commit |
| `execution-system.md` | execution/ | package | Code execution | Executor, LocalExecutor, ExecutionLimits |
| `prompt-system.md` | prompts/ | package | Prompt templates | SYSTEM, CODE_SYSTEM, loader |
| `types-and-exceptions.md` | core/ | module | Core types and errors | RunResult, FinalAnswer, exceptions |

### Architecture Documentation (`docs/architecture/`)

| File | Component | Depth | Purpose | Seams |
|------|-----------|-------|---------|-------|
| `README.md` | architecture/ | 2 | Architecture directory index | A |
| `agent-hierarchy.md` | agents/ | 1 | Agent inheritance and implementations | A |
| `design-patterns.md` | framework | 3 | Architectural and design patterns | A |
| `data-flow.md` | framework | 3 | Data transformation flows | A |
| `dependencies.md` | framework | 3 | Module dependencies and coupling | A |
| `memory-management.md` | memory/ | 2 | Memory architecture and strategies | A |
| `tool-calling-architecture.md` | tools/ | 2 | Tool registration and adapters | A |

### Modules Documentation (`docs/modules/`)

| File | Module | Type | Purpose | Key Exports | Seams |
|------|--------|------|---------|-------------|-------|
| `README.md` | modules/ | index | Module documentation index | N/A | - |
| `agents_base.md` | agents/base.py | class | BaseAgent abstract class | BaseAgent | M |
| `agents_react.md` | agents/react.py | class | ReactAgent implementation | ReactAgent | M |
| `agents_code.md` | agents/code.py | class | TinyCodeAgent implementation | TinyCodeAgent | M |
| `core_adapters.md` | core/adapters.py | protocol | Tool calling adapters | ToolCallingAdapter | M |
| `core_schema.md` | core/schema.py | function | Type hints to JSON schema | generate_schema | M |
| `core_parsing.md` | core/parsing.py | function | JSON parsing utilities | extract_json | M |
| `core_types.md` | core/types.py | class | Core data structures | RunResult, FinalAnswer | M |
| `core_exceptions.md` | core/exceptions.py | class | Custom exceptions | StepLimitReached, MultipleFinalAnswers | M |
| `core_finalizer.md` | core/finalizer.py | class | Final answer manager | Finalizer | M |
| `core_registry.md` | core/registry.py | function | Tool decorator and wrapper | tool, Tool | M |
| `execution_protocol.md` | execution/protocol.py | protocol | Executor interface | Executor | M |
| `execution_local.md` | execution/local.py | class | Local executor | LocalExecutor | M |
| `memory_manager.md` | memory/manager.py | class | Conversation history | MemoryManager | M |
| `prompts_templates.md` | prompts/templates.py | module | Prompt constants | SYSTEM, CODE_SYSTEM | M |
| `prompts_loader.md` | prompts/loader.py | function | Prompt loading | load_prompt | M |
| `tools_builtin.md` | tools/builtin/ | module | Standard tools | web_search, web_browse | M |
| `tools_validation.md` | tools/validation.py | function | Tool validation | validate_tool_class | M |
| `signals.md` | signals/primitives.py | function | Cognitive signals | uncertain, explore, commit | M |
| `limits.md` | limits/boundaries.py | class | Resource limits | ExecutionLimits | M |

### State Documentation (`docs/state/`)

| File | Component | Type | Purpose | Thread-Safe |
|------|-----------|------|---------|-------------|
| `state-summary.md` | state/ | index | State management summary | N/A |
| `agent-memory-overview.md` | AgentMemory | class | Working memory scratchpad | No |
| `memory-manager-overview.md` | MemoryManager | class | Conversation history | No |
| `global-state-stores.md` | framework | analysis | Global state patterns | No |
| `pruning-strategies.md` | memory/ | function | Memory pruning strategies | N/A |
| `caching-mechanisms.md` | framework | analysis | Caching status and plans | N/A |
| `step-history-tracking.md` | memory/steps.py | class | Step type definitions | N/A |

---

## SEAMS Summary

### Structure Layer

The structure documentation provides comprehensive coverage of the tinyAgent codebase organization:

**Key Findings:**
- **Layered Architecture**: Clear separation between agents (orchestration), core (abstractions), and implementation layers
- **Naming Conventions**: Consistent snake_case for files/functions, PascalCase for classes
- **Module Organization**: Each directory has focused, well-defined responsibility
- **Dependency Flow**: Agents depend on core abstractions, which depend on foundational types

**Architecture Pattern:**
```
Application Layer (User Code)
    ↓
Agent Layer (agents/)
    ↓
Abstraction Layer (core/)
    ↓
Implementation Layers (execution/, memory/, signals/, tools/)
```

**Seams Identified:**
- Tool registration via @tool decorator
- Executor protocol for swappable backends
- Memory strategy injection
- Prompt template override
- Adapter selection for LLM compatibility

### Entry Points Layer

The entry points documentation catalogs all public APIs and usage patterns:

**Key Findings:**
- **Two Agent Types**: ReactAgent (JSON tools) and TinyCodeAgent (Python execution)
- **Tool System**: Decorator-based with validation and multiple calling modes
- **Memory Systems**: Dual architecture (MemoryManager for history, AgentMemory for working state)
- **Execution Protocol**: Pluggable executors with graduated trust levels
- **Signaling System**: Cognitive primitives for observability

**Public API Surface:**
```python
# Primary entry points
from tinyagent import ReactAgent, TinyCodeAgent, tool

# Tool calling modes
from tinyagent import ToolCallingMode

# Memory management
from tinyagent import MemoryManager, AgentMemory

# Execution
from tinyagent import Executor, LocalExecutor, ExecutionLimits

# Types and exceptions
from tinyagent import RunResult, FinalAnswer, StepLimitReached
```

**Usage Patterns Documented:**
- Getting started with agents
- Creating custom tools
- Tool calling configuration
- Code execution patterns
- Memory management
- Custom prompts

### Architecture Layer

The architecture documentation analyzes design patterns, data flow, and module relationships:

**Key Findings:**

**Design Patterns:**
- **Adapter Pattern**: Tool calling adapters for different LLM capabilities
- **Protocol Pattern**: Executor interface for execution backends
- **Decorator Pattern**: Tool registration with validation
- **Strategy Pattern**: Memory pruning strategies
- **Observer Pattern**: Signal collection for observability
- **Singleton Pattern**: Finalizer for thread-safe final answers

**Data Flow (ReactAgent):**
```
User Request → Memory Initialization → ReAct Loop
    → LLM Request (with tools) → LLM Response
    → Adapter Extracts Tool Call → Tool Execution
    → Result Added to Memory → Loop (until final answer)
```

**Data Flow (TinyCodeAgent):**
```
User Request → MemoryManager Initialization → ReAct Loop
    → LLM Request → Python Code Generation
    → AST Validation → Executor.run(code)
    → Namespace Execution → stdout + Scratchpad
    → Memory Update → Loop (until final_answer())
```

**Agent Hierarchy:**
```
BaseAgent (abstract)
├── ReactAgent (JSON tool-calling)
└── TinyCodeAgent (Python code execution)
```

**Key Architectural Decisions:**
1. **Protocol-Based Design**: Loose coupling via Executor protocol
2. **Adapter Pattern**: Transparent LLM tool calling support
3. **Two-Tier Memory**: Separate conversation history from working memory
4. **Fail-Fast Validation**: Catch errors at definition time
5. **Graduated Trust**: Multiple security levels for code execution

### Modules Layer

The modules documentation provides detailed analysis of each component:

**Key Findings:**

**Agent Modules:**
- `BaseAgent`: Shared tool management infrastructure
- `ReactAgent`: ReAct pattern with JSON tool calling
- `TinyCodeAgent`: Python code generation with sandboxed execution

**Core Modules:**
- `adapters.py`: Multi-format tool calling abstraction
- `schema.py`: Type hints to JSON schema conversion
- `parsing.py`: Robust JSON parsing with wrapper handling
- `types.py`: Fundamental data structures (RunResult, FinalAnswer)
- `exceptions.py`: Specialized agent exceptions
- `finalizer.py`: Thread-safe final answer manager
- `registry.py`: Tool decorator and validation

**Execution Modules:**
- `protocol.py`: Standard interface for execution backends
- `local.py`: Sandboxed Python execution with namespace isolation

**Memory Modules:**
- `manager.py`: Conversation history with pruning strategies
- `steps.py`: Step type definitions (SystemPrompt, Task, Action, Scratchpad)

**Tool Modules:**
- `builtin/`: Standard tools (web search, planning, shell)
- `validation.py`: Static analysis for tool class structure

**Design Patterns by Module:**
- `adapters.py`: Adapter pattern
- `protocol.py`: Protocol pattern
- `registry.py`: Decorator pattern
- `manager.py`: Strategy pattern (pruning strategies)
- `finalizer.py`: Singleton pattern

### State Layer

The state documentation analyzes state management patterns and thread safety:

**Key Findings:**

**State Architecture:**
```
Global State (Thread-Unsafe)
├── _PLANS dict (tools/builtin/planning.py)
└── _signal_collector reference (signals/primitives.py)

Per-Agent State (Not Thread-Safe)
├── MemoryManager (conversation history)
└── AgentMemory (working memory)

Per-Run State (Thread-Safe)
└── Finalizer (final answer with Lock)
```

**State Components:**

| Component | Purpose | Lifetime | Thread-Safe |
|-----------|---------|----------|-------------|
| AgentMemory | Working memory scratchpad | Per-run | No |
| MemoryManager | Conversation history | Per-agent | No |
| Finalizer | Final answer state | Per-run | Yes (Lock) |
| _PLANS | Plan storage | Global | **No** (concern) |
| _signal_collector | Signal hooks | Global | **No** (concern) |

**Thread Safety Analysis:**
- **Safe**: Finalizer uses threading.Lock()
- **Unsafe**: MemoryManager, AgentMemory (assume single-threaded)
- **Concern**: Global state (_PLANS, _signal_collector) not thread-safe

**Token Management:**
- **Pruning Strategies**: keep_last_n_steps, prune_old_observations, no_pruning
- **Output Limits**: ExecutionLimits.max_output_bytes truncates tool output
- **Current Limitation**: No actual token counting, relies on heuristics

**Persistence Status:**
- **No persistence**: All state is in-memory only
- **No serialization**: State lost on process termination
- **No recovery**: Cannot restore from previous runs

**Design Patterns:**
- **Single-Assignment**: Finalizer ensures one final answer per run
- **Immutable History**: Step objects not modified after creation
- **Working Memory**: AgentMemory for explicit state tracking
- **Structured History**: Type-safe Step objects

---

## Quick Navigation

### By Documentation Type

- **[Structure Documentation](structure/)** - Directory organization and file structure
- **[Entry Points](entry/)** - Public APIs and usage documentation
- **[Architecture](architecture/)** - Design patterns, data flow, and module relationships
- **[Modules](modules/)** - Detailed component documentation
- **[State Management](state/)** - State patterns, thread safety, and lifecycle

### By Agent Type

- **[ReactAgent](entry/react-agent.md)** - JSON tool-calling agent
  - [Architecture](architecture/agent-hierarchy.md#reactagent)
  - [Module Details](modules/agents_react.md)
  - [Usage Examples](entry/react-agent.md#usage-example)

- **[TinyCodeAgent](entry/tinycode-agent.md)** - Python code execution agent
  - [Architecture](architecture/agent-hierarchy.md#tinycodeagent)
  - [Module Details](modules/agents_code.md)
  - [Execution System](entry/execution-system.md)

### By System Component

- **[Tool System](entry/tool-decorator.md)** - Tool creation and validation
  - [Architecture](architecture/tool-calling-architecture.md)
  - [Built-in Tools](entry/built-in-tools.md)
  - [Validation](entry/validation.md)

- **[Memory System](entry/memory-system.md)** - State management
  - [Architecture](architecture/memory-management.md)
  - [Manager](modules/memory_manager.md)
  - [State Summary](state/state-summary.md)

- **[Execution System](entry/execution-system.md)** - Code execution
  - [Protocol](modules/execution_protocol.md)
  - [Local Executor](modules/execution_local.md)
  - [Limits](modules/limits.md)

- **[Signals](entry/signals.md)** - Cognitive primitives
  - [Module](modules/signals.md)
  - [Usage](entry/signals.md)

### By Use Case

**Getting Started:**
1. [tinyagent Root Package](entry/tinyagent-root.md) - Main package exports
2. [ReactAgent](entry/react-agent.md) - Quick start guide
3. [Tool Decorator](entry/tool-decorator.md) - Creating custom tools

**Advanced Usage:**
1. [Tool Calling Architecture](architecture/tool-calling-architecture.md) - Adapter patterns
2. [Memory Management](architecture/memory-management.md) - Pruning strategies
3. [Execution Limits](entry/execution-system.md) - Resource management

**Contributing:**
1. [Structure Index](structure/INDEX.md) - Codebase organization
2. [Design Patterns](architecture/design-patterns.md) - Architectural patterns
3. [Dependencies](architecture/dependencies.md) - Module relationships
4. [Module Documentation](modules/README.md) - Component details

---

## Documentation Methodology

### Generation Process

These documents were generated using the **SEAMS (Synthesis of Extensive Agent Mapping System)** methodology with multiple specialized agents:

1. **Structure Agents** - Analyzed directory organization and file structure
2. **Entry Point Agents** - Cataloged public APIs and usage patterns
3. **Architecture Agents** - Identified design patterns and data flow
4. **Module Agents** - Documented component implementation details
5. **State Agents** - Analyzed state management and thread safety
6. **Synthesis Agent** - Aggregated findings into this unified map

### Analysis Depth

- **Depth 0**: Root directory structure
- **Depth 1**: Top-level directories (agents/, core/, execution/, etc.)
- **Depth 2**: Subdirectories and key modules
- **Depth 3**: Individual components and implementation details

### Frontmatter Standard

Each document includes required frontmatter:

```yaml
---
title: Human-readable name
path: relative/path/from/root
type: file|directory|index
depth: 0-3
description: One-line purpose summary
exports: [list, of, exports]  # For modules/entry only
seams: [A|E|M]  # Extensibility markers
---
```

**Seam Markers:**
- **A** = Architecture-level extension point
- **E** = Entry point for user code
- **M** = Module boundary

### Maintenance Guidelines

When updating the codebase:

1. **Update structure docs** when adding/removing directories
2. **Update entry docs** when changing public APIs
3. **Update architecture docs** when modifying design patterns
4. **Update module docs** when changing implementations
5. **Update state docs** when modifying state management
6. **Regenerate MAP.md** to reflect all changes
7. **Maintain frontmatter** consistency across all documents

---

## Key Architectural Insights

### Strengths

1. **Clear Layering**: Well-defined separation between agents, core, and implementation
2. **Protocol-Based Design**: Loose coupling enables easy testing and extension
3. **Adapter Pattern**: Transparent support for different LLM capabilities
4. **Dual Memory Architecture**: Appropriate separation of concerns
5. **Fail-Fast Validation**: Catches errors early with clear messages
6. **Comprehensive Tool System**: Flexible, validated, extensible

### Areas for Improvement

1. **Thread Safety**: Global state (_PLANS, _signal_collector) not thread-safe
2. **Token Counting**: No actual token counting, relies on heuristics
3. **Persistence**: No state persistence or recovery mechanisms
4. **Caching**: No result caching or memoization
5. **Observability**: Reserved directory but minimal implementation

### Extension Points

**For Framework Users:**
- Custom tools via @tool decorator
- Custom executors via Executor protocol
- Memory pruning strategies
- Prompt templates
- Tool calling adapters

**For Framework Contributors:**
- New agent types (inherit from BaseAgent)
- New execution backends (implement Executor)
- New memory strategies (implement PruneStrategy)
- New tool calling modes (implement ToolCallingAdapter)
- New signal types (add to signals/primitives.py)

---

## Codebase Health Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| **Architecture** | Excellent | Clear layering, minimal coupling |
| **Documentation** | Comprehensive | 58 docs, 14,360 lines |
| **Type Safety** | Good | Protocol-based, type hints throughout |
| **Testing** | Not Documented | Test coverage not analyzed |
| **Thread Safety** | Mixed | Finalizer safe, global state not |
| **Error Handling** | Excellent | Custom exceptions, fail-fast validation |
| **Extensibility** | Excellent | Multiple extension points |
| **Complexity** | Low-Medium | Simple patterns, clear abstractions |

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

### Key Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `@tool` | `core/registry.py` | Create tools from functions |
| `generate_schema` | `core/schema.py` | Type hints to JSON schema |
| `extract_json` | `core/parsing.py` | Parse JSON from LLM responses |
| `load_prompt` | `prompts/loader.py` | Load prompt from file |
| `validate_tool_class` | `tools/validation.py` | Validate tool class structure |

---

**Documentation Version:** 1.0.0
**Last Updated:** 2026-01-03 11:31:33 CST
**Generated by:** SEAMS Synthesis Agent
**Analysis Engine:** Gemini MCP (gemini-2.5-flash)
