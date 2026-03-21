# API Reference

Complete API documentation for the tinyagent package.

## Core Modules

| Module | Description |
|--------|-------------|
| [agent](agent.md) | `Agent` class - main entry point |
| [agent_types](agent_types.md) | Type definitions (messages, events, tools) |
| [agent_loop](agent_loop.md) | Core execution loop |
| [agent_tool_execution](agent_tool_execution.md) | Tool execution helpers |

## Features

| Module | Description |
|--------|-------------|
| [caching](caching.md) | Prompt caching for reduced cost and latency |
| [usage-semantics](usage-semantics.md) | Canonical usage contract and token semantics for the built-in provider path |

## Providers

| Module | Description |
|--------|-------------|
| [../alchemy-binding](../alchemy-binding.md) | Single source of truth for the Rust-backed alchemy integration and Python/Rust runtime flow |
| [providers](providers.md) | Optional alchemy binding adapter and Proxy providers |
| [openai-compatible-endpoints](openai-compatible-endpoints.md) | Using `OpenAICompatModel.base_url` with OpenAI-compatible endpoints |
| [usage-semantics](usage-semantics.md) | Canonical `usage` schema, field mapping, and precedence rules |

## Quick Reference

### Common Imports

```python
# Agent
from tinyagent import Agent, AgentOptions

# Types
from tinyagent import (
    AgentMessage,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    AgentTool,
    AgentToolResult,
    AgentEvent,
    AgentState,
)

# Providers
from tinyagent.alchemy_provider import (
    OpenAICompatModel,
    stream_alchemy_openai_completions,
)

# Helpers
from tinyagent import (
    extract_text,
    default_convert_to_llm,
)
```

### Type Hierarchy

```
AgentMessage
├── Message (LLM-compatible)
│   ├── UserMessage
│   ├── AssistantMessage
│   └── ToolResultMessage
└── CustomAgentMessage (custom roles)

AgentEvent
├── AgentStartEvent / AgentEndEvent
├── TurnStartEvent / TurnEndEvent
├── MessageStartEvent / MessageUpdateEvent / MessageEndEvent
└── ToolExecutionStartEvent / ToolExecutionUpdateEvent / ToolExecutionEndEvent

Content Types
├── TextContent
├── ImageContent
├── ThinkingContent
└── ToolCallContent
```

### Callback Signatures

```python
import asyncio
from typing import Awaitable, Callable
from tinyagent import AgentMessage, Message, AgentToolResult

# Convert messages before LLM call
ConvertToLlmCallback = Callable[
    [list[AgentMessage]],
    list[Message] | Awaitable[list[Message]]
]

# Transform context before LLM call
TransformContextCallback = Callable[
    [list[AgentMessage], asyncio.Event | None],
    Awaitable[list[AgentMessage]]
]

# Resolve API key dynamically
ApiKeyResolverCallback = Callable[
    [str],  # provider name
    str | None | Awaitable[str | None]
]

# Tool progress updates
AgentToolUpdateCallback = Callable[[AgentToolResult], None]
```

## Runtime Cutover Validation

After installing the optional external binding, validate the typed event/model
contract with the live harness:

```bash
uv run python docs/harness/tool_call_types_harness.py
```

The harness prints only model type names and performs one real tool-call validation.
```
