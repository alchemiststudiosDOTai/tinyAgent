"""Tool execution helpers for the agent loop."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

from pydantic import BaseModel, Field

from .agent_types import (
    AgentMessage,
    AgentTool,
    AgentToolResult,
    AssistantMessage,
    EventStream,
    JsonObject,
    MessageEndEvent,
    MessageStartEvent,
    TextContent,
    ToolCallContent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    ToolResultMessage,
)


class ToolExecutionResult(BaseModel):
    tool_results: list[ToolResultMessage] = Field(default_factory=list)
    steering_messages: list[AgentMessage] | None = None


def validate_tool_arguments(tool: AgentTool, tool_call: ToolCallContent) -> JsonObject:
    """Validate and normalize tool arguments.

    Some providers (e.g. MiniMax via alchemy) may return arguments as a JSON
    string rather than a parsed dict. Normalize to dict before execution.
    """

    del tool  # Arguments schema validation is deferred; normalize shape here.
    raw: object = tool_call.arguments

    if isinstance(raw, str):
        try:
            parsed = json.loads(raw) if raw else {}
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, ValueError):
            return {}

    return raw if isinstance(raw, dict) else {}


def _extract_tool_calls(assistant_message: AssistantMessage) -> list[ToolCallContent]:
    tool_calls: list[ToolCallContent] = []
    for content in assistant_message.content:
        if isinstance(content, ToolCallContent):
            tool_calls.append(content)
    return tool_calls


def _find_tool(tools: list[AgentTool] | None, name: str) -> AgentTool | None:
    if not tools:
        return None
    for tool in tools:
        if tool.name == name:
            return tool
    return None


def _is_parent_task_cancelling(parent_task: asyncio.Task[object] | None) -> bool:
    if parent_task is None:
        return False
    cancelling_attr = getattr(parent_task, "cancelling", None)
    if callable(cancelling_attr):
        cancelling_count = cancelling_attr()
        if isinstance(cancelling_count, int):
            return cancelling_count > 0
    return parent_task.cancelled()


async def _execute_single_tool(
    tool: AgentTool | None,
    tool_call: ToolCallContent,
    signal: asyncio.Event | None,
    stream: EventStream,
    parent_task: asyncio.Task[object] | None,
) -> tuple[AgentToolResult, bool]:
    """Execute a single tool and return (result, is_error)."""

    tool_call_name = tool_call.name or ""
    tool_call_id = tool_call.id or ""
    tool_call_args = tool_call.arguments

    if not tool:
        return (
            AgentToolResult(
                content=[TextContent(text=f"Tool {tool_call_name} not found")],
                details={},
            ),
            True,
        )
    if not tool.execute:
        error_text = f"Tool {tool_call_name} has no execute function"
        return (
            AgentToolResult(
                content=[TextContent(text=error_text)],
                details={},
            ),
            True,
        )

    try:
        validated_args = validate_tool_arguments(tool, tool_call)

        def on_update(partial_result: AgentToolResult) -> None:
            stream.push(
                ToolExecutionUpdateEvent(
                    tool_call_id=tool_call_id,
                    tool_name=tool_call_name,
                    args=tool_call_args,
                    partial_result=partial_result,
                )
            )

        result = await tool.execute(tool_call_id, validated_args, signal, on_update)
        return (result, False)
    except asyncio.CancelledError as exc:
        if _is_parent_task_cancelling(parent_task):
            raise
        message = str(exc) or "Tool execution cancelled"
        return (
            AgentToolResult(
                content=[TextContent(text=message)],
                details={},
            ),
            True,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            AgentToolResult(
                content=[TextContent(text=str(exc))],
                details={},
            ),
            True,
        )


def _create_tool_result_message(
    tool_call: ToolCallContent,
    result: AgentToolResult,
    is_error: bool,
) -> ToolResultMessage:
    return ToolResultMessage(
        tool_call_id=tool_call.id or "",
        tool_name=tool_call.name or "",
        content=result.content,
        details=result.details,
        is_error=is_error,
        timestamp=int(asyncio.get_running_loop().time() * 1000),
    )


async def execute_tool_calls(
    tools: list[AgentTool] | None,
    assistant_message: AssistantMessage,
    signal: asyncio.Event | None,
    stream: EventStream,
    get_steering_messages: Callable[[], Awaitable[list[AgentMessage]]] | None = None,
) -> ToolExecutionResult:
    tool_calls = _extract_tool_calls(assistant_message)
    if not tool_calls:
        return ToolExecutionResult()

    # Emit start events for all tools upfront
    for tool_call in tool_calls:
        stream.push(
            ToolExecutionStartEvent(
                tool_call_id=tool_call.id or "",
                tool_name=tool_call.name or "",
                args=tool_call.arguments,
            )
        )

    # Resolve tools and execute all in parallel
    resolved = [_find_tool(tools, tc.name or "") for tc in tool_calls]
    parent_task = asyncio.current_task()
    raw_results: list[tuple[AgentToolResult, bool]] = await asyncio.gather(
        *(
            _execute_single_tool(tool, tc, signal, stream, parent_task)
            for tool, tc in zip(resolved, tool_calls, strict=True)
        )
    )

    # Emit end events and build result messages in original order
    results: list[ToolResultMessage] = []
    for tool_call, (result, is_error) in zip(tool_calls, raw_results, strict=True):
        stream.push(
            ToolExecutionEndEvent(
                tool_call_id=tool_call.id or "",
                tool_name=tool_call.name or "",
                result=result,
                is_error=is_error,
            )
        )
        tool_result_message = _create_tool_result_message(tool_call, result, is_error)
        results.append(tool_result_message)
        stream.push(MessageStartEvent(message=tool_result_message))
        stream.push(MessageEndEvent(message=tool_result_message))

    # Check for steering messages once after all tools complete
    steering_messages: list[AgentMessage] | None = None
    if get_steering_messages:
        steering = await get_steering_messages()
        if steering:
            steering_messages = steering

    return ToolExecutionResult(tool_results=results, steering_messages=steering_messages)


def skip_tool_call(tool_call: ToolCallContent, stream: EventStream) -> ToolResultMessage:
    """Skip a tool call due to user interruption."""

    tool_call_name = tool_call.name or ""
    tool_call_id = tool_call.id or ""
    tool_call_args = tool_call.arguments

    result = AgentToolResult(
        content=[TextContent(text="Skipped due to queued user message.")],
        details={},
    )
    stream.push(
        ToolExecutionStartEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_call_name,
            args=tool_call_args,
        )
    )
    stream.push(
        ToolExecutionEndEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_call_name,
            result=result,
            is_error=True,
        )
    )

    tool_result_message = _create_tool_result_message(tool_call, result, True)

    stream.push(MessageStartEvent(message=tool_result_message))
    stream.push(MessageEndEvent(message=tool_result_message))

    return tool_result_message
