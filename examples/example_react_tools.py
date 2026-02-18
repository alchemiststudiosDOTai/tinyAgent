"""Full ReAct loop with tool calling via the Rust alchemy binding.

Uses an OpenAI-compatible endpoint (OpenRouter) to run a multi-step
math agent that calls tools, observes results, and reasons to a final answer.

## How the call flows

    agent.prompt("What is (15+27)*3?")
        │
        ▼
    ┌─────────────────────────────────────────────────┐
    │  Python: agent_loop (agent_loop.py)             │
    │  Builds messages list, calls stream_fn()        │
    └──────────────────┬──────────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────────┐
    │  Python: stream_fn → stream_alchemy_openai_...  │
    │  Converts model/context/opts to dicts,          │
    │  calls into Rust via _alchemy.so                │
    └──────────────────┬──────────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────────┐
    │  Rust (PyO3 abi3): openai_completions_stream()  │
    │  Opens HTTP connection via reqwest + tokio,     │
    │  parses SSE chunks, yields events to Python     │
    │  via blocking next_event() called in a thread   │
    └──────────────────┬──────────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────────┐
    │  OpenRouter (HTTPS)                             │
    │  POST /api/v1/chat/completions (streaming)      │
    │  → proxies to moonshotai/kimi-k2.5              │
    └──────────────────┬──────────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────────┐
    │  SSE chunks stream back through:                │
    │  OpenRouter → Rust (parse SSE) → Python         │
    │                                                 │
    │  Events: text_delta, tool_call_start,           │
    │          tool_call_delta, tool_call_end, done    │
    └──────────────────┬──────────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────────┐
    │  Python: agent_loop sees tool_calls stop_reason │
    │  → executes tools on Python side                │
    │  → appends tool results to messages             │
    │  → calls stream_fn() again (next turn)          │
    │  → repeats until stop_reason=complete           │
    └─────────────────────────────────────────────────┘

Usage:
    OPENROUTER_API_KEY=sk-or-v1-... python examples/example_react_tools.py
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from tinyagent import Agent, AgentOptions, extract_text
from tinyagent.agent_types import (
    AgentEvent,
    AgentTool,
    AgentToolResult,
    AgentToolUpdateCallback,
    Context,
    Model,
    SimpleStreamOptions,
    StreamResponse,
    TextContent,
)
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
if not API_KEY:
    raise SystemExit("Set OPENROUTER_API_KEY environment variable")


# ── Tools ──────────────────────────────────────────────────────────────
#
# AgentTool.execute is called by the agent loop with 4 positional args:
#   tool_call_id  – unique ID for this invocation (e.g. "functions.add:0")
#   args          – parsed JSON arguments as a dict (e.g. {"a": 15, "b": 27})
#   signal        – asyncio.Event for abort signaling (None if no abort)
#   on_update     – callback for partial results (streaming tool output)
#
# Return an AgentToolResult with content list.


async def execute_add(
    tool_call_id: str,
    args: dict[str, Any],
    signal: asyncio.Event | None,
    on_update: AgentToolUpdateCallback,
) -> AgentToolResult:
    a, b = args["a"], args["b"]
    result = a + b
    print(f"  [TOOL] add({a}, {b}) = {result}")
    return AgentToolResult(content=[TextContent(type="text", text=str(result))])


async def execute_multiply(
    tool_call_id: str,
    args: dict[str, Any],
    signal: asyncio.Event | None,
    on_update: AgentToolUpdateCallback,
) -> AgentToolResult:
    a, b = args["a"], args["b"]
    result = a * b
    print(f"  [TOOL] multiply({a}, {b}) = {result}")
    return AgentToolResult(content=[TextContent(type="text", text=str(result))])


add_tool = AgentTool(
    name="add",
    description="Add two numbers together",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"},
        },
        "required": ["a", "b"],
    },
    execute=execute_add,
)

multiply_tool = AgentTool(
    name="multiply",
    description="Multiply two numbers together",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"},
        },
        "required": ["a", "b"],
    },
    execute=execute_multiply,
)


# ── Model ──────────────────────────────────────────────────────────────
#
# OpenAICompatModel wraps any OpenAI-compatible chat/completions endpoint.
# The base_url points to the full endpoint path (not just the host).

model = OpenAICompatModel(
    provider="openrouter",
    id="moonshotai/kimi-k2.5",
    api="openai-completions",
    base_url="https://openrouter.ai/api/v1/chat/completions",
)


# ── Stream function ───────────────────────────────────────────────────
#
# The stream_fn bridges Python's agent loop to the Rust alchemy binding.
# It's called once per turn with (model, context, options).
#
# Inside stream_alchemy_openai_completions:
#   1. Python dicts are passed to Rust via PyO3 (pythonize)
#   2. Rust spawns a tokio task that opens an HTTP stream to OpenRouter
#   3. Returns a handle with blocking next_event()/result() methods
#   4. Python calls these in asyncio.to_thread() for async iteration


async def stream_fn(m: Model, ctx: Context, opts: SimpleStreamOptions) -> StreamResponse:
    """Wire the Rust alchemy provider as the stream function."""
    opts["api_key"] = API_KEY
    opts["temperature"] = 0.3
    opts["max_tokens"] = 1024
    return await stream_alchemy_openai_completions(m, ctx, opts)


# ── Event logger ──────────────────────────────────────────────────────
#
# agent.subscribe() registers a callback that fires for every event.
# Events flow: message_start → message_update* → message_end
#              tool_execution_start → tool_execution_end
#              turn_end → (next turn or agent_end)


def _ev(event: AgentEvent, key: str) -> object:
    """Extract a field from an event dict."""
    return event.get(key) if isinstance(event, dict) else getattr(event, key, None)


def _log_message_update(event: AgentEvent) -> None:
    """Handle streamed message_update events."""
    msg = _ev(event, "message")
    if not msg:
        return
    ame = _ev(event, "assistant_message_event")
    if not isinstance(ame, dict):
        return
    # Streamed text tokens arrive as text_delta events
    if ame.get("type") == "text_delta" and ame.get("delta"):
        print(ame["delta"], end="", flush=True)
    # Tool call events: the LLM wants to invoke a tool
    elif ame.get("type") == "tool_call_start":
        print(f"\n  [CALLING] {ame.get('name', '?')}", end="", flush=True)
    elif ame.get("type") == "tool_call_delta" and ame.get("arguments"):
        print(ame["arguments"], end="", flush=True)
    elif ame.get("type") == "tool_call_end":
        print()


def _log_turn_end(event: AgentEvent) -> None:
    """Log turn boundaries with stop reason."""
    # stop_reason="tool_calls" → loop will execute tools then call LLM again.
    # stop_reason="complete"   → agent is done.
    msg = _ev(event, "message")
    if not msg:
        return
    stop = msg.get("stop_reason") if isinstance(msg, dict) else None
    print(f"\n── turn end (stop_reason={stop}) ────────────────")


def event_logger(event: AgentEvent) -> None:
    """Print agent events as they happen."""
    etype = _ev(event, "type")

    if etype == "message_start":
        print("\n── LLM response ─────────────────────────────────")
    elif etype == "message_update":
        _log_message_update(event)
    elif etype == "tool_execution_start":
        # Agent loop is about to call tool.execute() on the Python side
        name = _ev(event, "tool_name")
        tc_id = _ev(event, "tool_call_id")
        print(f"  [EXEC] {name or '?'} (id={tc_id})")
    elif etype == "tool_execution_end":
        print(f"  [RESULT] {_ev(event, 'result')}")
    elif etype == "turn_end":
        _log_turn_end(event)
    elif etype == "agent_end":
        print("\n══ AGENT DONE ══════════════════════════════════")


# ── Main ──────────────────────────────────────────────────────────────


async def main() -> None:
    print("=" * 60)
    print("tinyagent — ReAct Tool-Calling Demo (Rust alchemy binding)")
    print(f"Model: {model.id} via OpenRouter")
    print("=" * 60)

    # 1. Create agent with our Rust-backed stream function
    agent = Agent(AgentOptions(stream_fn=stream_fn))

    # 2. Configure: system prompt tells the LLM to use tools
    agent.set_system_prompt(
        "You are a helpful math assistant. Use the provided tools to solve problems step by step. "
        "Always use tools for calculations — never calculate in your head."
    )

    # 3. Set model and register tools
    agent.set_model(model)
    agent.set_tools([add_tool, multiply_tool])

    # 4. Subscribe to events for real-time visibility
    agent.subscribe(event_logger)

    # 5. Send prompt — this kicks off the ReAct loop:
    #    prompt → LLM → tool_calls → execute tools → LLM → ... → complete
    question = "What is (15 + 27) * 3? Show your work."
    print(f"\nUser: {question}\n")

    result = await agent.prompt(question)
    print(f"\nFinal answer: {extract_text(result)}")


if __name__ == "__main__":
    asyncio.run(main())
