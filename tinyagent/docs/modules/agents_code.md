---
title: TinyCodeAgent
path: agents/code.py
type: file
depth: 1
description: Lightweight Python-executing ReAct agent acting as junior developer with sandboxed execution
exports: [TinyCodeAgent, TrustLevel]
seams: [M]
---

# agents/code.py

## Where
`/Users/tuna/tinyAgent/tinyagent/agents/code.py`

## What
Implements `TinyCodeAgent`, a Python-executing ReAct agent specializing in thinking and acting through code. Features sandboxed execution with graduated trust levels, intelligent retries, and clear task completion signals.

## How

### Key Classes

**TrustLevel (Enum)**
Defines execution isolation levels:
- `LOCAL`: Restricted `exec()` in same process (fast, trusted tools)
- `ISOLATED`: Subprocess with timeout (default, most uses)
- `SANDBOXED`: Container/VM (untrusted inputs, production)

**TinyCodeAgent(BaseAgent)**
- Inherits from `BaseAgent`
- Orchestrates ReAct loop using Python code execution
- Enforces execution limits (timeout, memory, output size)
- Handles LLM communication and code extraction

**Core Methods:**
- `__post_init__`: Initializes AsyncOpenAI client, selects executor based on trust level, loads system prompt
- `_init_executor`: Configures `LocalExecutor` (future: SubprocessExecutor, DockerExecutor) based on trust level, injects tools and signals
- `run`: Main entry point - manages ReAct loop, step limits, verbose logging, returns final result
- `_process_step`: Single iteration - sends messages to LLM, extracts code, executes, processes result
- `_handle_execution_error`, `_handle_timeout`, `_handle_final_result`: Specific outcome handlers
- `_add_observation`: Adds execution results and scratchpad context to memory, includes pruning logic
- `_chat`: Async OpenAI-compatible LLM call
- `_extract_code`: Static method to parse Python code blocks from LLM text response

**Special Features:**
- **Signal Integration**: `commit`, `explore`, `uncertain` signals injected as tools
- **Memory Pruning**: Old steps removed to manage context window
- **Code Extraction**: Robust parsing of ```python``` blocks
- **Error Recovery**: Specific handlers for different failure modes

## Why

**Design Rationale:**
- **ReAct Pattern**: Iterative reasoning and execution for complex problem-solving
- **Graduated Trust**: Flexible isolation balancing security, performance, and complexity
- **Modular Executor**: Swappable backends without changing agent logic
- **Persistent Memory**: `MemoryManager` and `AgentMemory` for multi-step reasoning
- **Explicit Signals**: LLM can communicate intent about task completion
- **Robust Error Handling**: Recovery mechanisms for execution failures

**Architectural Integration:**
- **agents package**: Specialized agent for code-based tasks
- **core.exceptions**: `StepLimitReached` for control flow
- **core.finalizer**: Output management
- **core.registry**: `Tool` definitions
- **core.types**: `RunResult` structure
- **execution**: `LocalExecutor` for code execution
- **limits**: `ExecutionLimits` for resource management
- **memory**: `MemoryManager`, `ActionStep`, `AgentMemory` for state
- **prompts**: System prompt loading and templates
- **signals**: `commit`, `explore`, `uncertain` for LLM communication

**Dependencies:**
- `agents.base.BaseAgent`: Base agent functionality
- `execution.local.LocalExecutor`: Code execution
- `limits.ExecutionLimits`: Resource constraints
- `memory.manager.MemoryManager`: Conversation management
- `memory.memory.AgentMemory`: Working memory
- `signals`: Cognitive signals
- `prompts.loader`: Prompt loading
- `prompts.templates.CODE_SYSTEM`: Code-specific prompts
