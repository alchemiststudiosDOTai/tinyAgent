# TinyAgent

A small, modular agent framework for building LLM-powered applications in Python.

## Overview

TinyAgent provides a lightweight foundation for creating conversational AI agents with tool use capabilities. It features:

- **Streaming-first architecture**: All LLM interactions support streaming responses
- **Tool execution**: Define and execute tools with structured outputs
- **Event-driven**: Subscribe to agent events for real-time UI updates
- **Provider agnostic**: Works with OpenRouter, proxy servers, or custom providers
- **Type-safe**: Full type hints throughout

## Quick Start

```python
import asyncio
from tinyagent import Agent, AgentOptions, OpenRouterModel, stream_openrouter

# Create an agent
agent = Agent(
    AgentOptions(
        stream_fn=stream_openrouter,
        session_id="my-session"
    )
)

# Configure
agent.set_system_prompt("You are a helpful assistant.")
agent.set_model(OpenRouterModel(id="anthropic/claude-3.5-sonnet"))

# Simple prompt
async def main():
    response = await agent.prompt_text("What is the capital of France?")
    print(response)

asyncio.run(main())
```

## Installation

```bash
pip install tinyagent
```

## Core Concepts

### Agent

The [`Agent`](api/agent.md) class is the main entry point. It manages:

- Conversation state (messages, tools, system prompt)
- Streaming responses
- Tool execution
- Event subscription

### Messages

Messages follow a typed dictionary structure:

- `UserMessage`: Input from the user
- `AssistantMessage`: Response from the LLM
- `ToolResultMessage`: Result from tool execution

### Tools

Tools are functions the LLM can call:

```python
from tinyagent import AgentTool, AgentToolResult

async def calculate_sum(tool_call_id: str, args: dict, signal, on_update) -> AgentToolResult:
    result = args["a"] + args["b"]
    return AgentToolResult(
        content=[{"type": "text", "text": str(result)}]
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

## Documentation

- [Architecture](ARCHITECTURE.md): System design and component interactions
- [API Reference](api/): Detailed module documentation

## Project Structure

```
tinyagent/
├── agent.py              # Agent class
├── agent_loop.py         # Core agent execution loop
├── agent_tool_execution.py  # Tool execution helpers
├── agent_types.py        # Type definitions
├── openrouter_provider.py   # OpenRouter integration
├── alchemy_provider.py   # Rust-based provider
├── proxy.py              # Proxy server integration
└── proxy_event_handlers.py  # Proxy event parsing
```
