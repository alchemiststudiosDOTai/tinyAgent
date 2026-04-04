---
title: MiniMax Single Tool Call Example
summary: One minimal MiniMax live example showing OpenAI-style tool calling through TinyAgent.
when_to_read:
  - When wiring a MiniMax tool-calling example
  - When checking the smallest useful end-to-end tool call setup
last_updated: "2026-04-04"
ontological_relations:
  - extends: openai-compatible-endpoints.md
  - implemented_by: ../../docs/harness/tool_call_types_harness.py
  - composes_with: agent.md#AgentOptions
  - composes_with: providers.md#minimax-endpoints
---

# MiniMax Single Tool Call Example

This is the smallest useful live MiniMax tool-calling example in TinyAgent.

It shows one tool:

- defined with OpenAI-style `parameters`
- exposed to the model via `AgentTool`
- called once by MiniMax
- returned as a `ToolResultMessage`
- followed by a short final assistant answer

## Requirements

- `tinyagent._alchemy` available in this repo, either by:
  - using a wheel that already includes the extension, or
  - building the in-repo `rust/` crate and staging the artifact into `tinyagent/`
- `MINIMAX_API_KEY` set in `.env`

Example `.env`:

```dotenv
MINIMAX_API_KEY=your-key-here
MINIMAX_MODEL=MiniMax-M2.5
MINIMAX_BASE_URL=https://api.minimax.io/v1/chat/completions
```

## Minimal example

```python
import asyncio
import os
from collections.abc import Callable

from tinyagent import Agent, AgentOptions, AgentTool, AgentToolResult
from tinyagent.agent_types import JsonObject, TextContent
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions


def resolve_api_key(provider: str) -> str | None:
    if provider.lower() == "minimax":
        return os.getenv("MINIMAX_API_KEY")
    return None


async def add_numbers(
    tool_call_id: str,
    args: JsonObject,
    signal: asyncio.Event | None,
    on_update: Callable[[AgentToolResult], None],
) -> AgentToolResult:
    del tool_call_id, signal, on_update
    a = float(args["a"])
    b = float(args["b"])
    return AgentToolResult(
        content=[TextContent(text=str(int(a + b)))],
        details={
            "input": {"a": a, "b": b},
            "output": {"sum": a + b},
        },
    )


async def main() -> None:
    agent = Agent(
        AgentOptions(
            stream_fn=stream_alchemy_openai_completions,
            get_api_key=resolve_api_key,
            session_id="minimax-single-tool-example",
        )
    )

    agent.set_model(
        OpenAICompatModel(
            provider="minimax",
            api="minimax-completions",
            id=os.getenv("MINIMAX_MODEL", "MiniMax-M2.5"),
            base_url=os.getenv(
                "MINIMAX_BASE_URL",
                "https://api.minimax.io/v1/chat/completions",
            ),
            max_tokens=128,
        )
    )

    agent.set_tools(
        [
            AgentTool(
                name="add_numbers",
                description="Add two numbers and return the sum.",
                parameters={
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"},
                    },
                    "required": ["a", "b"],
                },
                execute=add_numbers,
            )
        ]
    )

    agent.set_system_prompt(
        "You are a strict tool-using assistant. "
        "Call add_numbers exactly once before answering. "
        "Do not do the arithmetic yourself."
    )

    result = await agent.prompt(
        "Use add_numbers exactly once with a=17 and b=25. "
        "After the tool returns, answer with one short sentence."
    )
    print(result)


asyncio.run(main())
```

For a caching-specific live probe after exporting `.env` values into the shell, run:

```bash
set -a
source .env >/dev/null 2>&1
set +a
uv run python examples/example_caching.py
```

The probe defaults to MiniMax, but you can override provider, model, base URL,
API key, and session via `CACHE_PROBE_*` environment variables.

For tool-contract validation in this repo, run:

```bash
uv run python docs/harness/tool_call_types_harness.py
```

## Tool schema

The MiniMax request uses an OpenAI-compatible tool definition:

```json
{
  "type": "object",
  "properties": {
    "a": {"type": "number"},
    "b": {"type": "number"}
  },
  "required": ["a", "b"]
}
```

## Expected flow

1. The user prompt asks the model to use `add_numbers`.
2. MiniMax emits a tool call with JSON arguments.
3. TinyAgent executes `add_numbers`.
4. The tool returns an `AgentToolResult`.
5. TinyAgent appends a `ToolResultMessage`.
6. MiniMax sends the final natural-language answer.

## Expected result

Typical final answer:

```text
The sum of 17 and 25 is 42.
```

Typical tool result details:

```json
{
  "input": {
    "a": 17.0,
    "b": 25.0
  },
  "output": {
    "sum": 42.0
  }
}
```

## Typical event sequence

Assistant stream events commonly include:

- `start`
- `thinking_start`, `thinking_delta`, `thinking_end`
- `tool_call_start`, `tool_call_delta`, `tool_call_end`
- `text_start`, `text_delta`, `text_end`
- `done`

Agent events commonly include:

- `agent_start`
- `turn_start`
- `message_start`
- `message_update`
- `message_end`
- `tool_execution_start`
- `tool_execution_end`
- `turn_end`
- `agent_end`

## Validation

To validate the live typed contract in this repo, run:

```bash
uv run python docs/harness/tool_call_types_harness.py
```

That harness performs one real tool-calling turn and prints the observed type names and event categories.
