#!/usr/bin/env python3
"""Example: TinyAgent + MiniMax + tool calling via Rust alchemy binding.

Prereqs:
  - Build extension from repo root: maturin develop --release
  - Set MINIMAX_API_KEY in env or .env

Run:
  uv run python examples/example_minimax_alchemy_tools.py
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from dotenv import load_dotenv

from tinyagent import Agent, AgentOptions, extract_text
from tinyagent.agent_types import AgentEvent, AgentTool, AgentToolResult, TextContent
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

DEFAULT_MINIMAX_BASE_URL = "https://api.minimax.io/v1/chat/completions"
DEFAULT_MINIMAX_MODEL = "MiniMax-M2.5"


async def execute_add(
    tool_call_id: str,
    args: dict[str, Any],
    signal: asyncio.Event | None,
    on_update: Any,
) -> AgentToolResult:
    a = float(args["a"])
    b = float(args["b"])
    value = a + b
    print(f"\n[tool] add({a}, {b}) = {value}")
    return AgentToolResult(content=[TextContent(type="text", text=str(value))])


async def execute_multiply(
    tool_call_id: str,
    args: dict[str, Any],
    signal: asyncio.Event | None,
    on_update: Any,
) -> AgentToolResult:
    a = float(args["a"])
    b = float(args["b"])
    value = a * b
    print(f"\n[tool] multiply({a}, {b}) = {value}")
    return AgentToolResult(content=[TextContent(type="text", text=str(value))])


def _event_type(event: AgentEvent) -> str | None:
    if isinstance(event, dict):
        return event.get("type")
    return getattr(event, "type", None)


def log_tool_events(event: AgentEvent) -> None:
    etype = _event_type(event)
    if etype == "tool_execution_start":
        if isinstance(event, dict):
            print(f"[tool-start] {event.get('tool_name')} ({event.get('tool_call_id')})")
        else:
            print(f"[tool-start] {event.tool_name} ({event.tool_call_id})")
    elif etype == "tool_execution_end":
        if isinstance(event, dict):
            print(f"[tool-end] {event.get('tool_name')}")
        else:
            print(f"[tool-end] {event.tool_name}")


async def main() -> None:
    load_dotenv()

    if not os.getenv("MINIMAX_API_KEY"):
        print("Missing MINIMAX_API_KEY. Add it to your env or .env file.")
        return

    add_tool = AgentTool(
        name="add",
        description="Add two numbers",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
        execute=execute_add,
    )

    multiply_tool = AgentTool(
        name="multiply",
        description="Multiply two numbers",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
        execute=execute_multiply,
    )

    agent = Agent(AgentOptions(stream_fn=stream_alchemy_openai_completions))
    agent.set_system_prompt(
        "You are a calculator assistant. "
        "For arithmetic, you must call available tools and then answer with only the final number."
    )
    agent.set_tools([add_tool, multiply_tool])
    agent.set_model(
        OpenAICompatModel(
            provider="minimax",
            api="minimax-completions",
            id=os.getenv("MINIMAX_MODEL", DEFAULT_MINIMAX_MODEL),
            base_url=os.getenv("MINIMAX_BASE_URL", DEFAULT_MINIMAX_BASE_URL),
        )
    )

    unsub = agent.subscribe(log_tool_events)
    try:
        prompt = "Compute (15 + 27) * 3 using tools."
        print(f"Prompt: {prompt}")
        message = await agent.prompt(prompt)
        print(f"Final: {extract_text(message)}")
    finally:
        unsub()


if __name__ == "__main__":
    asyncio.run(main())
