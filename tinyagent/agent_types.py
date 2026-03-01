"""Type definitions for the agent loop."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Protocol, TypeAlias, TypeVar, Union, cast

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypeAliasType

# ------------------------------
# JSON-ish helper types
# ------------------------------

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue = TypeAliasType(
    "JsonValue",
    "JsonPrimitive | list[JsonValue] | dict[str, JsonValue]",
)
JsonObject: TypeAlias = dict[str, JsonValue]

ZERO_USAGE: JsonObject = {
    "input": 0,
    "output": 0,
    "cache_read": 0,
    "cache_write": 0,
    "total_tokens": 0,
    "cost": {
        "input": 0.0,
        "output": 0.0,
        "cache_read": 0.0,
        "cache_write": 0.0,
        "total": 0.0,
    },
}


# ------------------------------
# Core message/content types
# ------------------------------


class _AgentBaseModel(BaseModel):
    """Shared model configuration for migrated message/state models."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")


class ThinkingBudgets(_AgentBaseModel):
    """Token budgets for thinking/reasoning."""

    thinking_budget: int | None = None
    max_tokens: int | None = None


TResult = TypeVar("TResult")

MaybeAwaitable: TypeAlias = TResult | Awaitable[TResult]


class ThinkingLevel(str, Enum):
    """Thinking/reasoning level for models that support it."""

    OFF = "off"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class CacheControl(_AgentBaseModel):
    """Cache control directive for Anthropic prompt caching."""

    type: str | None = None


class TextContent(_AgentBaseModel):
    """Text content block."""

    type: Literal["text"] = "text"
    text: str | None = None
    text_signature: str | None = None
    cache_control: CacheControl | None = None


class ImageContent(_AgentBaseModel):
    """Image content block."""

    type: Literal["image"] = "image"
    url: str | None = None
    mime_type: str | None = None


class ThinkingContent(_AgentBaseModel):
    """Thinking content block."""

    type: Literal["thinking"] = "thinking"
    thinking: str | None = None
    thinking_signature: str | None = None
    cache_control: CacheControl | None = None


class ToolCallContent(_AgentBaseModel):
    """Tool call content block."""

    type: Literal["tool_call"] = "tool_call"
    id: str | None = None
    name: str | None = None
    arguments: JsonObject = Field(default_factory=dict)
    partial_json: str | None = None


ToolCall: TypeAlias = ToolCallContent

AssistantContent: TypeAlias = TextContent | ThinkingContent | ToolCallContent


class UserMessage(_AgentBaseModel):
    """User message for LLM."""

    role: Literal["user"] = "user"
    content: list[TextContent | ImageContent] = Field(default_factory=list)
    timestamp: int | None = None


StopReason: TypeAlias = Literal[
    "complete",
    "error",
    "aborted",
    "tool_calls",
    "stop",
    "length",
    "tool_use",
]

STOP_REASONS: frozenset[StopReason] = frozenset(
    {
        "complete",
        "error",
        "aborted",
        "tool_calls",
        "stop",
        "length",
        "tool_use",
    }
)


class AssistantMessage(_AgentBaseModel):
    """Assistant message from LLM."""

    role: Literal["assistant"] = "assistant"
    content: list[AssistantContent | None] = Field(default_factory=list)
    stop_reason: StopReason | None = None
    timestamp: int | None = None
    api: str | None = None
    provider: str | None = None
    model: str | None = None
    usage: JsonObject | None = None
    error_message: str | None = None


class ToolResultMessage(_AgentBaseModel):
    """Tool result message."""

    role: Literal["tool_result"] = "tool_result"
    tool_call_id: str | None = None
    tool_name: str | None = None
    content: list[TextContent | ImageContent] = Field(default_factory=list)
    details: JsonObject = Field(default_factory=dict)
    is_error: bool = False
    timestamp: int | None = None


Message = Union[UserMessage, AssistantMessage, ToolResultMessage]


class CustomAgentMessage(_AgentBaseModel):
    """Base class for custom agent messages."""

    role: str = ""
    timestamp: int | None = None


AgentMessage = Union[Message, CustomAgentMessage]


ConvertToLlmFn: TypeAlias = Callable[[list[AgentMessage]], MaybeAwaitable[list[Message]]]
TransformContextFn: TypeAlias = Callable[
    [list[AgentMessage], asyncio.Event | None],
    Awaitable[list[AgentMessage]],
]
ApiKeyResolver: TypeAlias = Callable[[str], MaybeAwaitable[str | None]]
AgentMessageProvider: TypeAlias = Callable[[], Awaitable[list[AgentMessage]]]


# ------------------------------
# Tool types
# ------------------------------


@dataclass
class AgentToolResult:
    """Result from executing a tool."""

    content: list[TextContent | ImageContent] = field(default_factory=list)
    details: JsonObject = field(default_factory=dict)


AgentToolUpdateCallback = Callable[[AgentToolResult], None]


@dataclass
class Tool:
    """Tool definition."""

    name: str = ""
    description: str = ""
    parameters: JsonObject = field(default_factory=dict)


@dataclass
class AgentTool(Tool):
    """Agent tool with execute function."""

    label: str = ""
    execute: Callable[..., Awaitable[AgentToolResult]] | None = None


# ------------------------------
# Context/model types
# ------------------------------


@dataclass
class Context:
    """Context for LLM calls."""

    system_prompt: str = ""
    messages: list[Message] = field(default_factory=list)
    tools: list[AgentTool] | None = None


@dataclass
class AgentContext:
    """Agent context with AgentMessage types."""

    system_prompt: str = ""
    messages: list[AgentMessage] = field(default_factory=list)
    tools: list[AgentTool] | None = None


@dataclass
class Model:
    """Model configuration."""

    provider: str = ""
    id: str = ""  # Model identifier (e.g., "gpt-4", "claude-3.5-sonnet")
    api: str = ""  # API type (e.g., "openai", "anthropic", "openrouter")
    thinking_level: ThinkingLevel = ThinkingLevel.OFF


class SimpleStreamOptions(_AgentBaseModel):
    """Standard stream options passed to providers."""

    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    signal: asyncio.Event | None = None


StreamFn: TypeAlias = Callable[[Model, Context, SimpleStreamOptions], Awaitable["StreamResponse"]]


class AssistantMessageEvent(_AgentBaseModel):
    """Event during assistant message streaming."""

    type: (
        Literal[
            "start",
            "text_start",
            "text_delta",
            "text_end",
            "thinking_start",
            "thinking_delta",
            "thinking_end",
            "tool_call_start",
            "tool_call_delta",
            "tool_call_end",
            "done",
            "error",
        ]
        | None
    ) = None
    partial: AssistantMessage | None = None
    content_index: int | None = None
    delta: str | None = None
    content: str | TextContent | ThinkingContent | ToolCallContent | None = None
    tool_call: ToolCallContent | None = None
    reason: str | None = None
    message: AssistantMessage | None = None
    error: AssistantMessage | str | None = None


STREAM_UPDATE_EVENTS: frozenset[str] = frozenset(
    {
        "text_start",
        "text_delta",
        "text_end",
        "thinking_start",
        "thinking_delta",
        "thinking_end",
        "tool_call_start",
        "tool_call_delta",
        "tool_call_end",
    }
)


class StreamResponse(Protocol):
    """Response from streaming."""

    def result(self) -> Awaitable[AssistantMessage]: ...

    def __aiter__(self) -> AsyncIterator[AssistantMessageEvent]: ...

    async def __anext__(self) -> AssistantMessageEvent: ...


# ------------------------------
# Agent event types
# ------------------------------


@dataclass
class AgentStartEvent:
    type: Literal["agent_start"] = "agent_start"


@dataclass
class AgentEndEvent:
    type: Literal["agent_end"] = "agent_end"
    messages: list[AgentMessage] = field(default_factory=list)


@dataclass
class TurnStartEvent:
    type: Literal["turn_start"] = "turn_start"


@dataclass
class TurnEndEvent:
    type: Literal["turn_end"] = "turn_end"
    message: AgentMessage | None = None
    tool_results: list[ToolResultMessage] = field(default_factory=list)


@dataclass
class MessageStartEvent:
    type: Literal["message_start"] = "message_start"
    message: AgentMessage | None = None


@dataclass
class MessageUpdateEvent:
    type: Literal["message_update"] = "message_update"
    message: AgentMessage | None = None
    assistant_message_event: AssistantMessageEvent | None = None


@dataclass
class MessageEndEvent:
    type: Literal["message_end"] = "message_end"
    message: AgentMessage | None = None


@dataclass
class ToolExecutionStartEvent:
    type: Literal["tool_execution_start"] = "tool_execution_start"
    tool_call_id: str = ""
    tool_name: str = ""
    args: JsonObject | None = None


@dataclass
class ToolExecutionUpdateEvent:
    type: Literal["tool_execution_update"] = "tool_execution_update"
    tool_call_id: str = ""
    tool_name: str = ""
    args: JsonObject | None = None
    partial_result: AgentToolResult | None = None


@dataclass
class ToolExecutionEndEvent:
    type: Literal["tool_execution_end"] = "tool_execution_end"
    tool_call_id: str = ""
    tool_name: str = ""
    result: AgentToolResult | None = None
    is_error: bool = False


AgentEvent = Union[
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    TurnEndEvent,
    MessageStartEvent,
    MessageUpdateEvent,
    MessageEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    ToolExecutionEndEvent,
]


@dataclass
class AgentLoopConfig:
    """Configuration for the agent loop."""

    model: Model
    convert_to_llm: ConvertToLlmFn
    transform_context: TransformContextFn | None = None
    get_api_key: ApiKeyResolver | None = None
    get_steering_messages: AgentMessageProvider | None = None
    get_follow_up_messages: AgentMessageProvider | None = None
    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class AgentState(_AgentBaseModel):
    """Agent state containing all configuration and conversation data."""

    system_prompt: str = ""
    model: Model | None = None
    thinking_level: ThinkingLevel = ThinkingLevel.OFF
    tools: list[AgentTool] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    is_streaming: bool = False
    stream_message: AgentMessage | None = None
    pending_tool_calls: set[str] = Field(default_factory=set)
    error: str | None = None


class EventStream:
    """Async event stream that yields events and returns a final result.

    Important: Some agent loops run in background tasks via `asyncio.create_task()`.
    If that background task fails, we must propagate the exception to the consumer
    of the stream. Otherwise callers awaiting `agent.prompt()` can hang forever.
    """

    _WAKEUP_SENTINEL = object()

    def __init__(
        self,
        is_end_event: Callable[[AgentEvent], bool],
        get_result: Callable[[AgentEvent], list[AgentMessage]],
    ):
        self._queue: asyncio.Queue[AgentEvent | object] = asyncio.Queue()
        self._is_end_event = is_end_event
        self._get_result = get_result
        self._result: list[AgentMessage] | None = None
        self._ended = False
        self._exception: BaseException | None = None

    def push(self, event: AgentEvent) -> None:
        if self._ended:
            return
        self._queue.put_nowait(event)

    def end(self, result: list[AgentMessage]) -> None:
        self._result = result
        self._ended = True
        self._queue.put_nowait(self._WAKEUP_SENTINEL)

    def set_exception(self, exc: BaseException) -> None:
        """Terminate the stream with an exception.

        The next consumer read will raise `exc` once all already-queued events
        are drained.
        """

        if self._ended:
            return
        self._exception = exc
        self._ended = True
        self._queue.put_nowait(self._WAKEUP_SENTINEL)

    def __aiter__(self) -> AsyncIterator[AgentEvent]:
        return self

    async def __anext__(self) -> AgentEvent:
        while True:
            if self._queue.empty():
                if self._exception is not None:
                    exc = self._exception
                    self._exception = None
                    raise exc
                if self._ended:
                    raise StopAsyncIteration

            queued_item = await self._queue.get()
            if queued_item is self._WAKEUP_SENTINEL:
                if self._exception is not None:
                    exc = self._exception
                    self._exception = None
                    raise exc
                if self._ended:
                    raise StopAsyncIteration
                continue

            event = cast(AgentEvent, queued_item)
            if self._is_end_event(event):
                self._result = self._get_result(event)
                self._ended = True
            return event

    async def result(self) -> list[AgentMessage]:
        while True:
            if self._queue.empty() and self._exception is not None:
                exc = self._exception
                self._exception = None
                raise exc
            if self._ended and self._queue.empty():
                break
            try:
                await self.__anext__()
            except StopAsyncIteration:
                break

        return self._result or []
