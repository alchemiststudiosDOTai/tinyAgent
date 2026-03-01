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
    AgentEndEvent,
    AgentEvent,
    AgentTool,
    AgentToolResult,
    AgentToolUpdateCallback,
    AssistantMessage,
    AssistantMessageEvent,
    Context,
    MessageStartEvent,
    MessageUpdateEvent,
    Model,
    SimpleStreamOptions,
    StreamResponse,
    TextContent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    TurnEndEvent,
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
    opts.api_key = API_KEY
    opts.temperature = 0.3
    opts.max_tokens = 1024
    return await stream_alchemy_openai_completions(m, ctx, opts)


# ── Event logger ──────────────────────────────────────────────────────
#
# agent.subscribe() registers a callback that fires for every event.
# Events flow: message_start → message_update* → message_end
#              tool_execution_start → tool_execution_end
#              turn_end → (next turn or agent_end)


def _log_model_assistant_event(ame: AssistantMessageEvent) -> None:
    """Print updates from model-typed assistant message events."""
    if ame.type == "text_delta" and ame.delta:
        print(ame.delta, end="", flush=True)
        return

    if ame.type == "tool_call_start":
        tool_name = ame.tool_call.name if ame.tool_call and ame.tool_call.name else "?"
        print(f"\n  [CALLING] {tool_name}", end="", flush=True)
        return

    if ame.type == "tool_call_delta" and ame.tool_call and ame.tool_call.arguments:
        print(str(ame.tool_call.arguments), end="", flush=True)
        return

    if ame.type == "tool_call_end":
        print()


def _log_message_update(event: MessageUpdateEvent) -> None:
    """Handle streamed message_update events."""
    if event.message is None:
        return
    ame = event.assistant_message_event
    if ame is None:
        return
    _log_model_assistant_event(ame)


def _log_turn_end(event: TurnEndEvent) -> None:
    """Log turn boundaries with stop reason."""
    # stop_reason="tool_calls" → loop will execute tools then call LLM again.
    # stop_reason="complete"   → agent is done.
    msg = event.message
    stop = msg.stop_reason if isinstance(msg, AssistantMessage) else None
    print(f"\n── turn end (stop_reason={stop}) ────────────────")


def event_logger(event: AgentEvent) -> None:
    """Print agent events as they happen."""

    if isinstance(event, MessageStartEvent):
        print("\n── LLM response ─────────────────────────────────")
    elif isinstance(event, MessageUpdateEvent):
        _log_message_update(event)
    elif isinstance(event, ToolExecutionStartEvent):
        # Agent loop is about to call tool.execute() on the Python side
        print(f"  [EXEC] {event.tool_name or '?'} (id={event.tool_call_id})")
    elif isinstance(event, ToolExecutionEndEvent):
        print(f"  [RESULT] {event.result}")
    elif isinstance(event, TurnEndEvent):
        _log_turn_end(event)
    elif isinstance(event, AgentEndEvent):
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
