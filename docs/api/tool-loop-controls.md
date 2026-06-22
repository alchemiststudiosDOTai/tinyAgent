---
title: Tool Loop Controls
when_to_read:
  - When a host needs to stop repeated tool-call loops
  - When adding policy around tool execution
  - When deciding between terminal tool results and host hooks
summary: Guide to terminal tool results and host-side tool-loop control hooks.
last_updated: "2026-06-21"
---

# Tool Loop Controls

TinyAgent supports host-side controls for ending repeated tool-call loops without
raising an abort or relying on an outer timeout. This guide documents the public
surface added by PR #40, `[codex] add host-side tool loop controls`.

Use these controls when the application can tell the next model turn is not
useful, unsafe, or allowed by policy. The agent still emits the normal tool
execution, message, turn, and agent end events, so consumers see a completed run
instead of a cancelled stream.

## Control Points

| Control | Runs | Use when |
|---------|------|----------|
| `AgentToolResult(terminate=True)` | Inside a tool implementation | The tool itself knows the run should stop after this result |
| `before_tool_call` | Before each tool executes | The host should block or replace a tool call before side effects happen |
| `after_tool_call` | After each tool result is built, before events are emitted | The host should inspect, replace, mark error, or terminate based on the result |
| `should_stop_after_turn` | After a turn completes | The host should decide whether another model turn is allowed |

`terminate` is host-side metadata. It is excluded from `ToolResultMessage`
serialization, so providers do not receive it as part of the LLM message payload.

## Terminal Tool Results

Return a terminal result when the tool has enough local context to end the run:

```python
from tinyagent import AgentToolResult, TextContent


async def search(tool_call_id, args, signal, on_update):
    if args["query"] in {"same query", "same query again"}:
        return AgentToolResult(
            content=[TextContent(text="Stopping after repeated search arguments.")],
            details={"policy": "repeated-search"},
            terminate=True,
        )

    return AgentToolResult(content=[TextContent(text="search result")])
```

The current tool batch still finishes and emits result events. The agent then
emits `turn_end` and `agent_end` without asking the model for another turn.

## Before Tool Call

Use `before_tool_call` for host policy that should run before the tool's side
effects:

```python
from tinyagent import Agent, AgentOptions, AgentToolResult, TextContent, ToolLoopControl


async def before_tool_call(tool_call, tool, args):
    if tool_call.name == "delete_file":
        return ToolLoopControl(
            result=AgentToolResult(
                content=[TextContent(text="Blocked by host policy.")],
                details={"policy": "no-delete-file"},
            ),
            is_error=True,
            terminate=True,
        )

    return None


agent = Agent(
    AgentOptions(
        stream_fn=stream_fn,
        before_tool_call=before_tool_call,
    )
)
```

Returning `ToolLoopControl(result=...)` supplies the structured tool result and
skips the tool execution. Returning `None` lets the tool run normally.

## After Tool Call

Use `after_tool_call` when the host needs to inspect or replace a completed tool
result before subscribers see it:

```python
from tinyagent import AgentToolResult, TextContent, ToolLoopControl


async def after_tool_call(tool_call, result_message):
    if result_message.details.get("quota_exhausted"):
        return ToolLoopControl(
            result=AgentToolResult(
                content=[TextContent(text="Quota exhausted. Stopping now.")],
                details={"policy": "quota"},
            ),
            is_error=True,
            terminate=True,
        )

    return None
```

The replacement result is emitted in the original tool-call order. Marking the
control terminal prevents steering from being polled after that batch and stops
the run after `turn_end`.

## Stop After Turn

Use `should_stop_after_turn` for policies that need the assistant message, all
tool results from the turn, the current context, and any newly queued messages:

```python
async def should_stop_after_turn(message, tool_results, context, new_messages):
    error_count = sum(result.is_error for result in tool_results)
    return error_count >= 3


agent = Agent(
    AgentOptions(
        stream_fn=stream_fn,
        should_stop_after_turn=should_stop_after_turn,
    )
)
```

When the callback returns `True`, TinyAgent ends the run cleanly instead of
starting another model turn.

## Execution Semantics

Tool execution remains parallel. `before_tool_call` runs for each extracted tool
call, unblocked tools execute concurrently, and `after_tool_call` runs before
final result events are emitted. Result messages are still emitted in the
assistant's original tool-call order.

A terminal result or hook does not cancel already-started tools in the same
batch. It marks the batch terminal, preserves normal event ordering, skips
post-batch steering, and ends the agent run before another LLM call.

These controls live above provider streaming. They work the same way with the
in-repo `tinyagent._alchemy` provider path, the proxy provider, or a custom
`StreamFn`.
