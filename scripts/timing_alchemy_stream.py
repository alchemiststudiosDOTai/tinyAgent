#!/usr/bin/env python3
"""Measure binding/provider stream timing for a plain query and a tool-call prompt.

Usage:
  uv run python scripts/timing_alchemy_stream.py

The script loads `.env`, picks the first configured provider using the same
precedence as the live harness, runs each scenario `TIMING_RUNS` times
(default: 3), and prints per-run timings plus mean first-event latency.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from statistics import mean
from time import perf_counter

from dotenv import load_dotenv

from tinyagent.agent_types import (
    AgentTool,
    Context,
    SimpleStreamOptions,
    TextContent,
    ToolCallContent,
    UserMessage,
)
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_CHUTES_BASE_URL = "https://llm.chutes.ai/v1/chat/completions"
DEFAULT_MINIMAX_BASE_URL = "https://api.minimax.io/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "google/gemini-2.0-flash-001"
DEFAULT_CHUTES_MODEL = "Qwen/Qwen3-Coder-Next-TEE"
DEFAULT_MINIMAX_MODEL = "MiniMax-M2.5"
DEFAULT_RUNS = 3
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_MAX_TOKENS = 256


@dataclass(frozen=True)
class RunMeasurement:
    scenario: str
    run_index: int
    open_ms: float
    first_event_ms: float
    stream_ms: float
    result_ms: float
    total_ms: float
    event_count: int
    first_event_type: str
    stop_reason: str | None
    saw_tool_call: bool


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _resolve_provider_and_model() -> OpenAICompatModel | None:
    max_tokens = int(os.getenv("TIMING_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
    if os.getenv("OPENROUTER_API_KEY"):
        return OpenAICompatModel(
            provider="openrouter",
            api="openai-completions",
            id=os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
            base_url=os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL),
            max_tokens=max_tokens,
        )
    if os.getenv("CHUTES_API_KEY"):
        return OpenAICompatModel(
            provider="chutes",
            api="openai-completions",
            id=os.getenv("CHUTES_MODEL", DEFAULT_CHUTES_MODEL),
            base_url=os.getenv("CHUTES_BASE_URL", DEFAULT_CHUTES_BASE_URL),
            max_tokens=max_tokens,
        )
    if os.getenv("MINIMAX_API_KEY"):
        return OpenAICompatModel(
            provider="minimax",
            api="minimax-completions",
            id=os.getenv("MINIMAX_MODEL", DEFAULT_MINIMAX_MODEL),
            base_url=os.getenv("MINIMAX_BASE_URL", DEFAULT_MINIMAX_BASE_URL),
            max_tokens=max_tokens,
        )
    return None


def _resolve_api_key(provider: str) -> str | None:
    env_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "chutes": "CHUTES_API_KEY",
        "openai": "OPENAI_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "minimax-cn": "MINIMAX_CN_API_KEY",
    }
    env_key = env_map.get(provider.lower())
    if env_key is None:
        return None
    return os.getenv(env_key)


def _plain_context() -> Context:
    return Context(
        system_prompt="You are a latency test assistant. Respond with plain text only.",
        messages=[
            UserMessage(
                content=[TextContent(text="Reply with exactly: latency-ok")]
            )
        ],
    )


def _tool_context() -> Context:
    return Context(
        system_prompt=(
            "You are a latency test assistant. "
            "You must call the provided tool exactly once and do not answer with plain text "
            "before the tool call."
        ),
        messages=[
            UserMessage(
                content=[
                    TextContent(
                        text="Call add_numbers exactly once with a=17 and b=25."
                    )
                ]
            )
        ],
        tools=[
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
            )
        ],
    )


async def _measure_once(
    *,
    scenario: str,
    run_index: int,
    model: OpenAICompatModel,
    options: SimpleStreamOptions,
    expect_tool_call: bool,
) -> RunMeasurement:
    context = _tool_context() if expect_tool_call else _plain_context()
    started_at = perf_counter()
    response = await stream_alchemy_openai_completions(model, context, options)
    opened_at = perf_counter()

    event_count = 0
    first_event_ms: float | None = None
    first_event_type: str | None = None
    saw_tool_call = False

    async for event in response:
        now = perf_counter()
        event_count += 1
        if first_event_ms is None:
            first_event_ms = (now - started_at) * 1000.0
            first_event_type = event.type or "unknown"
        if event.type in {"tool_call_start", "tool_call_delta", "tool_call_end"}:
            saw_tool_call = True
        if isinstance(event.tool_call, ToolCallContent):
            saw_tool_call = True

    stream_done_at = perf_counter()
    final_message = await response.result()
    finished_at = perf_counter()

    if any(isinstance(item, ToolCallContent) for item in final_message.content if item is not None):
        saw_tool_call = True
    if first_event_ms is None or first_event_type is None:
        raise RuntimeError(f"{scenario} run {run_index}: stream returned no events")
    if expect_tool_call and not saw_tool_call:
        raise RuntimeError(f"{scenario} run {run_index}: expected a tool call but none arrived")

    return RunMeasurement(
        scenario=scenario,
        run_index=run_index,
        open_ms=(opened_at - started_at) * 1000.0,
        first_event_ms=first_event_ms,
        stream_ms=(stream_done_at - started_at) * 1000.0,
        result_ms=(finished_at - stream_done_at) * 1000.0,
        total_ms=(finished_at - started_at) * 1000.0,
        event_count=event_count,
        first_event_type=first_event_type,
        stop_reason=final_message.stop_reason,
        saw_tool_call=saw_tool_call,
    )


def _print_run(measurement: RunMeasurement) -> None:
    print(
        f"scenario={measurement.scenario} "
        f"run={measurement.run_index} "
        f"open_ms={measurement.open_ms:.1f} "
        f"first_event_ms={measurement.first_event_ms:.1f} "
        f"stream_ms={measurement.stream_ms:.1f} "
        f"result_ms={measurement.result_ms:.1f} "
        f"total_ms={measurement.total_ms:.1f} "
        f"events={measurement.event_count} "
        f"first_event_type={measurement.first_event_type} "
        f"stop_reason={measurement.stop_reason or 'none'} "
        f"saw_tool_call={'yes' if measurement.saw_tool_call else 'no'}"
    )


def _print_summary(scenario: str, runs: list[RunMeasurement]) -> None:
    print(
        f"scenario={scenario} "
        f"mean_open_ms={mean(item.open_ms for item in runs):.1f} "
        f"mean_first_event_ms={mean(item.first_event_ms for item in runs):.1f} "
        f"mean_stream_ms={mean(item.stream_ms for item in runs):.1f} "
        f"mean_result_ms={mean(item.result_ms for item in runs):.1f} "
        f"mean_total_ms={mean(item.total_ms for item in runs):.1f}"
    )


async def main() -> None:
    load_dotenv()

    model = _resolve_provider_and_model()
    if model is None:
        print("SKIPPED: missing OPENROUTER_API_KEY, CHUTES_API_KEY, or MINIMAX_API_KEY")
        return

    api_key = _resolve_api_key(model.provider)
    if not api_key:
        raise RuntimeError(f"Missing API key for provider={model.provider}")

    runs = int(os.getenv("TIMING_RUNS", str(DEFAULT_RUNS)))
    timeout_seconds = float(os.getenv("TIMING_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    options = SimpleStreamOptions(
        api_key=api_key,
        temperature=0.0,
        max_tokens=int(os.getenv("TIMING_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
    )

    print(f"provider={model.provider}")
    print(f"model={model.id}")
    print(f"api={model.api}")
    print(f"runs={runs}")
    print(f"timeout_seconds={timeout_seconds:.1f}")
    print(f"binding_debug={'on' if _env_flag('TINYAGENT_ALCHEMY_DEBUG') else 'off'}")

    plain_runs: list[RunMeasurement] = []
    tool_runs: list[RunMeasurement] = []

    for run_index in range(1, runs + 1):
        plain = await asyncio.wait_for(
            _measure_once(
                scenario="plain_query",
                run_index=run_index,
                model=model,
                options=options,
                expect_tool_call=False,
            ),
            timeout=timeout_seconds,
        )
        plain_runs.append(plain)
        _print_run(plain)

    _print_summary("plain_query", plain_runs)

    for run_index in range(1, runs + 1):
        tool = await asyncio.wait_for(
            _measure_once(
                scenario="tool_call",
                run_index=run_index,
                model=model,
                options=options,
                expect_tool_call=True,
            ),
            timeout=timeout_seconds,
        )
        tool_runs.append(tool)
        _print_run(tool)

    _print_summary("tool_call", tool_runs)


if __name__ == "__main__":
    asyncio.run(main())
