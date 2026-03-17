# TinyAgent

![tinyAgent Logo](https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/master/static/images/new-ta-logo.jpg)

A small, modular agent framework for building LLM-powered applications in Python.

Inspired by [smolagents](https://github.com/huggingface/smolagents) and [Pi](https://github.com/badlogic/pi-mono) — borrowing the minimal-abstraction philosophy from the former and the conversational agent loop from the latter.

> **Beta** — TinyAgent is usable but not production-ready. APIs may change between minor versions.

> **Note:** The optional `tinyagent._alchemy` binding now lives in
> `https://github.com/tunahorse/tinyagent-alchemy` and is not built from this repo.

## Overview

TinyAgent provides a lightweight foundation for creating conversational AI agents with tool use capabilities. It features:

- **Streaming-first architecture**: All LLM interactions support streaming responses
- **Tool execution**: Define and execute tools with structured outputs
- **Event-driven**: Subscribe to agent events for real-time UI updates
- **Provider agnostic**: Works with any OpenAI-compatible `/chat/completions` endpoint (OpenRouter, OpenAI, Chutes, local servers)
- **Prompt caching**: Reduce token costs and latency with Anthropic-style cache breakpoints
- **Provider paths**: Optional external alchemy binding adapter plus proxy integration
- **Type-safe**: Full type hints throughout

## Quick Start

This example uses the optional `tinyagent._alchemy` binding via
`tinyagent.alchemy_provider`. Install that binding from the external repo first,
or use the proxy path instead.

```python
import asyncio
from tinyagent import Agent, AgentOptions
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

# Create an agent
agent = Agent(
    AgentOptions(
        stream_fn=stream_alchemy_openai_completions,
        session_id="my-session"
    )
)

# Configure
agent.set_system_prompt("You are a helpful assistant.")
agent.set_model(
    OpenAICompatModel(
        provider="openrouter",
        id="anthropic/claude-3.5-sonnet",
        base_url="https://openrouter.ai/api/v1/chat/completions",
    )
)
# Optional: any OpenAI-compatible /chat/completions endpoint
# agent.set_model(OpenAICompatModel(provider="openai", id="gpt-4o-mini", base_url="https://api.openai.com/v1/chat/completions"))

# Simple prompt
async def main():
    response = await agent.prompt_text("What is the capital of France?")
    print(response)

asyncio.run(main())
```

## Installation

```bash
pip install tiny-agent-os
```

Optional binding:

- Install/build `tinyagent._alchemy` from `https://github.com/tunahorse/tinyagent-alchemy`
  if you want `stream_alchemy_openai_completions`
- Otherwise, use the proxy path in `tinyagent.proxy`

## Core Concepts

### Agent

The [`Agent`](api/agent.md) class is the main entry point. It manages:

- Conversation state (messages, tools, system prompt)
- Streaming responses
- Tool execution
- Event subscription

### Messages

Messages are Pydantic models (use attribute access):

- `UserMessage`: Input from the user
- `AssistantMessage`: Response from the LLM
- `ToolResultMessage`: Result from tool execution

### Tools

Tools are functions the LLM can call:

```python
from tinyagent import AgentTool, AgentToolResult, TextContent

async def calculate_sum(tool_call_id: str, args: dict, signal, on_update) -> AgentToolResult:
    result = args["a"] + args["b"]
    return AgentToolResult(
        content=[TextContent(text=str(result))]
    )

tool = AgentTool(
    name="sum",
    description="Add two numbers",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"}
        },
        "required": ["a", "b"]
    },
    execute=calculate_sum
)

agent.set_tools([tool])
```

### Events

The agent emits events during execution:

- `AgentStartEvent` / `AgentEndEvent`: Agent run lifecycle
- `TurnStartEvent` / `TurnEndEvent`: Single turn lifecycle
- `MessageStartEvent` / `MessageUpdateEvent` / `MessageEndEvent`: Message streaming
- `ToolExecutionStartEvent` / `ToolExecutionUpdateEvent` / `ToolExecutionEndEvent`: Tool execution

Subscribe to events:

```python
def on_event(event):
    print(f"Event: {event.type}")

unsubscribe = agent.subscribe(on_event)
```

### Prompt Caching

TinyAgent supports [Anthropic-style prompt caching](api/caching.md) to reduce costs on multi-turn conversations. Enable it when creating the agent:

```python
agent = Agent(
    AgentOptions(
        stream_fn=stream_alchemy_openai_completions,
        session_id="my-session",
        enable_prompt_caching=True,
    )
)
```

Cache breakpoints are automatically placed on user message content blocks so the prompt prefix stays cached across turns. See [Prompt Caching](api/caching.md) for details.

## Optional Binding: `tinyagent._alchemy`

This repo keeps `tinyagent/alchemy_provider.py` as a compatibility adapter for the
optional external `tinyagent._alchemy` extension. The binding source, build
instructions, and low-level binding API now live in:

- `https://github.com/tunahorse/tinyagent-alchemy`

The compiled path is still useful when you want OpenAI-compatible streaming
without routing through a separate proxy, but it is no longer bundled or built
from this repository.

### Using via TinyAgent

You don't need to call the Rust binding directly. Use the `alchemy_provider` module:

```python
from tinyagent import Agent, AgentOptions
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

agent = Agent(
    AgentOptions(
        stream_fn=stream_alchemy_openai_completions,
        session_id="my-session",
    )
)
agent.set_model(
    OpenAICompatModel(
        provider="openrouter",
        id="anthropic/claude-3.5-sonnet",
        base_url="https://openrouter.ai/api/v1/chat/completions",
    )
)
```

MiniMax global:
```python
agent.set_model(
    OpenAICompatModel(
        provider="minimax",
        id="MiniMax-M2.5",
        base_url="https://api.minimax.io/v1/chat/completions",
        # api is optional here; inferred as "minimax-completions"
    )
)
```

MiniMax CN:
```python
agent.set_model(
    OpenAICompatModel(
        provider="minimax-cn",
        id="MiniMax-M2.5",
        base_url="https://api.minimax.chat/v1/chat/completions",
        # api is optional here; inferred as "minimax-completions"
    )
)
```

Smoke validation after installing the external binding:

- `uv run python scripts/smoke_rust_tool_calls_three_providers.py`


### Limitations

- The optional binding currently dispatches only `openai-completions` and
  `minimax-completions`.
- Image blocks are not yet supported (text and thinking blocks work).
- `next_event()` is blocking and runs in a thread via `asyncio.to_thread` -- this adds
  slight overhead compared to a native async generator, but keeps the GIL released during
  the native work.

## Documentation

- [Architecture](ARCHITECTURE.md): System design and component interactions
- [API Reference](api/): Detailed module documentation
- [Prompt Caching](api/caching.md): Cache breakpoints, cost savings, and provider requirements
- [OpenAI-Compatible Endpoints](api/openai-compatible-endpoints.md): Using `OpenAICompatModel.base_url` with OpenRouter/OpenAI/Chutes-compatible backends
- [Usage Semantics](api/usage-semantics.md): Canonical `usage` schema across provider flows
- [Harness Rules](../rules/README.md): ast-grep rules for the live tool-call harness
- [Changelog](../CHANGELOG.md): Release history
- [Shipping the alchemy binding](docs/releasing-alchemy-binding.md): Release workflow for wheels that include `tinyagent._alchemy`

## Project Structure

```
tinyagent/
├── agent.py              # Agent class
├── agent_loop.py         # Core agent execution loop
├── agent_tool_execution.py  # Tool execution helpers
├── agent_types.py        # Type definitions
├── caching.py            # Prompt caching utilities
├── alchemy_provider.py   # Adapter for the optional external binding
├── proxy.py              # Proxy server integration
└── proxy_event_handlers.py  # Proxy event parsing
```
