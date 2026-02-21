#!/usr/bin/env python3
"""Run one Agent across OpenRouter, MiniMax, and Chutes with tool calling.

Prereqs:
  - Build extension from repo root: maturin develop --release
  - Set OPENROUTER_API_KEY, MINIMAX_API_KEY, and CHUTES_API_KEY in .env

Run:
  uv run python examples/example_tool_calls_three_providers.py
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv

from tinyagent import Agent, AgentOptions, extract_text
from tinyagent.agent_types import AgentEvent, AgentTool, AgentToolResult, Model, TextContent
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MINIMAX_BASE_URL = "https://api.minimax.io/v1/chat/completions"
CHUTES_BASE_URL = "https://llm.chutes.ai/v1/chat/completions"

TOOL_PROMPT = (
    "Use the add_numbers tool exactly once with a=17 and b=25. Return only the numeric result."
)


@dataclass(frozen=True)
class ProviderRun:
    name: str
    provider: str
    required_key_env: str
    model: Model


@dataclass
class ProviderRunCapture:
    provider: str
    tool_starts: list[dict[str, str]] = field(default_factory=list)
    tool_ends: list[dict[str, str]] = field(default_factory=list)
    tool_results: list[dict[str, str]] = field(default_factory=list)
    stop_reason: str = ""
    final_text: str = ""
    error_message: str = ""


async def execute_add_numbers(
    tool_call_id: str,
    args: dict[str, Any],
    signal: asyncio.Event | None,
    on_update: Any,
) -> AgentToolResult:
    a = float(args["a"])
    b = float(args["b"])
    result = a + b
    return AgentToolResult(content=[TextContent(type="text", text=str(int(result)))])


def _event_type(event: AgentEvent) -> str | None:
    if isinstance(event, dict):
        value = event.get("type")
        return value if isinstance(value, str) else None
    value = getattr(event, "type", None)
    return value if isinstance(value, str) else None


def _event_attr(event: AgentEvent, key: str) -> str:
    value = event.get(key) if isinstance(event, dict) else getattr(event, key, "")
    return value if isinstance(value, str) else ""


def _resolve_api_key(provider: str) -> str | None:
    env_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "chutes": "CHUTES_API_KEY",
    }
    env_key = env_map.get(provider.lower())
    if not env_key:
        return None
    return os.getenv(env_key)


def _build_runs() -> list[ProviderRun]:
    return [
        ProviderRun(
            name="openrouter",
            provider="openrouter",
            required_key_env="OPENROUTER_API_KEY",
            model=OpenAICompatModel(
                provider="openrouter",
                api="openai-completions",
                id=os.getenv("OPENROUTER_MODEL", "moonshotai/kimi-k2.5"),
                base_url=os.getenv("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL),
            ),
        ),
        ProviderRun(
            name="minimax",
            provider="minimax",
            required_key_env="MINIMAX_API_KEY",
            model=OpenAICompatModel(
                provider="minimax",
                api="minimax-completions",
                id=os.getenv("MINIMAX_MODEL", "MiniMax-M2.5"),
                base_url=os.getenv("MINIMAX_BASE_URL", MINIMAX_BASE_URL),
            ),
        ),
        ProviderRun(
            name="chutes",
            provider="chutes",
            required_key_env="CHUTES_API_KEY",
            model=OpenAICompatModel(
                provider="chutes",
                api="openai-completions",
                id=os.getenv("CHUTES_MODEL", "Qwen/Qwen3-32B"),
                base_url=os.getenv("CHUTES_BASE_URL", CHUTES_BASE_URL),
            ),
        ),
    ]


async def run_provider(agent: Agent, run: ProviderRun) -> ProviderRunCapture:
    capture = ProviderRunCapture(provider=run.name)

    def on_event(event: AgentEvent) -> None:
        etype = _event_type(event)
        if etype == "tool_execution_start":
            capture.tool_starts.append(
                {
                    "tool_name": _event_attr(event, "tool_name"),
                    "tool_call_id": _event_attr(event, "tool_call_id"),
                }
            )
        elif etype == "tool_execution_end":
            capture.tool_ends.append(
                {
                    "tool_name": _event_attr(event, "tool_name"),
                    "tool_call_id": _event_attr(event, "tool_call_id"),
                }
            )

    agent.clear_messages()
    agent.set_model(run.model)
    unsubscribe = agent.subscribe(on_event)
    try:
        message = await agent.prompt(TOOL_PROMPT)
    finally:
        unsubscribe()

    capture.stop_reason = str(message.get("stop_reason") or "")
    capture.final_text = extract_text(message)
    capture.error_message = str(message.get("error_message") or "")

    for msg in agent.state.get("messages", []):
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "tool_result":
            continue
        capture.tool_results.append(
            {
                "tool_name": str(msg.get("tool_name") or ""),
                "tool_call_id": str(msg.get("tool_call_id") or ""),
            }
        )

    return capture


def print_capture(capture: ProviderRunCapture) -> None:
    print(f"\n=== {capture.provider} ===")
    print(f"stop_reason: {capture.stop_reason}")
    print(f"final_text: {capture.final_text}")
    print(f"error_message: {capture.error_message}")
    print(f"tool_execution_start: {json.dumps(capture.tool_starts, ensure_ascii=False)}")
    print(f"tool_execution_end: {json.dumps(capture.tool_ends, ensure_ascii=False)}")
    print(f"tool_results: {json.dumps(capture.tool_results, ensure_ascii=False)}")


async def main() -> None:
    load_dotenv()

    runs = _build_runs()
    missing = [run.required_key_env for run in runs if not os.getenv(run.required_key_env)]
    if missing:
        print(f"Missing required keys: {', '.join(missing)}")
        return

    add_tool = AgentTool(
        name="add_numbers",
        description="Add two numeric values and return the sum.",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
        execute=execute_add_numbers,
    )

    agent = Agent(
        AgentOptions(
            stream_fn=stream_alchemy_openai_completions,
            get_api_key=_resolve_api_key,
        )
    )
    agent.set_system_prompt(
        "You are a calculator assistant. For arithmetic, you must call add_numbers exactly once."
    )
    agent.set_tools([add_tool])

    captures: list[ProviderRunCapture] = []
    for run in runs:
        captures.append(await run_provider(agent, run))

    print("\nCross-provider tool-call smoke run complete.")
    for capture in captures:
        print_capture(capture)


if __name__ == "__main__":
    asyncio.run(main())
