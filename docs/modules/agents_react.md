---
title: ReactAgent
path: agents/react.py
type: file
depth: 1
description: ReAct (Reason + Act) pattern agent for JSON-tool calling with iterative reasoning loop
exports: [ReactAgent]
seams: [M]
---

# agents/react.py

## Where
`/Users/tuna/tinyAgent/tinyagent/agents/react.py`

## What
Implements `ReactAgent`, a minimal, typed agent following the ReAct (Reason + Act) paradigm designed for JSON-tool calling. Orchestrates iterative reasoning, tool execution, and observation cycles.

## How

### Key Classes

**ReactAgent(BaseAgent)**
- Inherits from `BaseAgent` gaining tool management capabilities
- Configurable with tools, model name, API key, system prompt file, temperature, token limits
- Uses `ToolCallingAdapter` for model-specific tool calling formats
- Maintains internal `Memory` instance for conversation history

**Core Methods:**
- `__post_init__`: Initializes OpenAI client, sets up adapter based on mode, initializes Memory, loads system prompt
- `run`: Public entry point - executes ReAct loop until final answer or `max_steps` reached
- `_process_step`: Handles single ReAct cycle - calls LLM, extracts tool calls, manages scratchpad, determines next action
- `_execute_tool`: Invokes specified tool with arguments, captures result, adds to memory
- `_chat`: Async call to OpenAI API, prepares messages and tool definitions per adapter requirements
- `_safe_tool`: Executes tool function with error handling and argument binding validation
- `_attempt_final_answer`: Fallback mechanism when step limit reached without explicit answer

**ReAct Flow:**
1. Thought: LLM generates reasoning
2. Action: LLM outputs JSON tool call or final answer
3. Observation: Tool execution result fed back to LLM
4. Repeat until final answer or step limit

**Error Handling:**
- Invalid JSON responses from LLM
- Tool validation failures
- Tool execution exceptions

## Why

**Design Rationale:**
- **ReAct Pattern**: Structured approach for LLMs to tackle complex problems through iterative reasoning and action
- **JSON-Tool Calling**: Explicit, parseable tool calls less prone to misinterpretation than free-form text
- **Modularity**: `ToolCallingAdapter` allows supporting different LLM providers without modifying core logic
- **State Management**: `Memory` and `Finalizer` ensure context maintenance and clean output
- **Safety**: `_safe_tool` wrapper prevents malformed arguments from causing crashes

**Architectural Integration:**
- **agents package**: Concrete implementation of agent interface
- **core.adapters**: Uses `ToolCallingAdapter` for LLM-specific formats
- **core.memory**: `Memory` class for interaction history
- **core.registry**: `Tool` definitions for available operations
- **core.exceptions**: `StepLimitReached` for control flow
- **prompts**: System prompt loading and templates

**Dependencies:**
- `agents.base.BaseAgent`: Base agent functionality
- `core.adapters`: Tool calling abstraction
- `core.memory`: Conversation management
- `core.registry`: Tool definitions
- `core.exceptions`: Error types
- `core.types`: RunResult
- `prompts.loader`: Prompt loading
- `prompts.templates`: Default prompts
