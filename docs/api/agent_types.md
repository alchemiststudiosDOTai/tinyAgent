# Agent Types Module

Type definitions for the TinyAgent runtime.

All runtime message/event/state contracts are Pydantic models (not `TypedDict`) so
code paths should use constructor/accessor style APIs instead of dict indexing.

## Content Types

### TextContent

```python
class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str | None = None
    text_signature: str | None = None
    cache_control: CacheControl | None = None
```

Text block in a message.

### ImageContent

```python
class ImageContent(BaseModel):
    type: Literal["image"] = "image"
    url: str | None = None
    mime_type: str | None = None
```

Image block (for vision-capable providers).

### ThinkingContent

```python
class ThinkingContent(BaseModel):
    type: Literal["thinking"] = "thinking"
    thinking: str | None = None
    thinking_signature: str | None = None
    cache_control: CacheControl | None = None
```

Reasoning/thinking block returned by models with reasoning capability.

### ToolCallContent

```python
class ToolCallContent(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    id: str | None = None
    name: str | None = None
    arguments: JsonObject = Field(default_factory=dict)
    partial_json: str | None = None
```

### AssistantContent

```python
AssistantContent = TextContent | ThinkingContent | ToolCallContent
```

Union of all supported assistant content blocks.

### CacheControl

```python
class CacheControl(BaseModel):
    type: str | None = None
```

Used for Anthropic-style prompt caching.

## Message Types

### UserMessage

```python
class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: list[TextContent | ImageContent] = Field(default_factory=list)
    timestamp: int | None = None
```

### AssistantMessage

```python
StopReason = Literal[
    "complete", "error", "aborted", "tool_calls", "stop", "length", "tool_use"
]

class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: list[AssistantContent | None] = Field(default_factory=list)
    stop_reason: StopReason | None = None
    timestamp: int | None = None
    api: str | None = None
    provider: str | None = None
    model: str | None = None
    usage: JsonObject | None = None
    error_message: str | None = None
```

### ToolResultMessage

```python
class ToolResultMessage(BaseModel):
    role: Literal["tool_result"] = "tool_result"
    tool_call_id: str | None = None
    tool_name: str | None = None
    content: list[TextContent | ImageContent] = Field(default_factory=list)
    details: JsonObject = Field(default_factory=dict)
    is_error: bool = False
    timestamp: int | None = None
```

### Message

```python
Message = Union[UserMessage, AssistantMessage, ToolResultMessage]
```

LLM-boundary-compatible messages.

### AgentMessage

```python
class CustomAgentMessage(BaseModel):
    role: str = ""
    timestamp: int | None = None

AgentMessage = Union[Message, CustomAgentMessage]
```

Internal agent messages may include custom roles.

## Tool Types

### Tool

```python
@dataclass
class Tool:
    name: str = ""
    description: str = ""
    parameters: JsonObject = field(default_factory=dict)
```

### AgentTool

```python
@dataclass
class AgentTool(Tool):
    label: str = ""
    execute: Callable[..., Awaitable[AgentToolResult]] | None = None
```

### AgentToolResult

```python
@dataclass
class AgentToolResult:
    content: list[TextContent | ImageContent] = field(default_factory=list)
    details: JsonObject = field(default_factory=dict)
```

## Context Types

### Context

```python
@dataclass
class Context:
    system_prompt: str = ""
    messages: list[Message] = field(default_factory=list)
    tools: list[AgentTool] | None = None
```

LLM-boundary context passed to providers.

### AgentContext

```python
@dataclass
class AgentContext:
    system_prompt: str = ""
    messages: list[AgentMessage] = field(default_factory=list)
    tools: list[AgentTool] | None = None
```

Internal context used by `agent_loop`.

## Model Types

### ThinkingLevel

```python
class ThinkingLevel(str, Enum):
    OFF = "off"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
```

### Model

```python
class Model(BaseModel):
    provider: str = ""
    id: str = ""
    api: str = ""
    thinking_level: ThinkingLevel = ThinkingLevel.OFF
```

Base model configuration used by all provider streams.

### SimpleStreamOptions

```python
class SimpleStreamOptions(BaseModel):
    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    signal: asyncio.Event | None = None
```

Options passed to provider stream functions.

## Event Types

### AssistantMessageEvent

```python
class AssistantMessageEvent(BaseModel):
    type: Literal[
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
    ] | None = None
    partial: AssistantMessage | None = None
    content_index: int | None = None
    delta: str | None = None
    content: str | TextContent | ThinkingContent | ToolCallContent | None = None
    tool_call: ToolCallContent | None = None
    reason: str | None = None
    message: AssistantMessage | None = None
    error: AssistantMessage | str | None = None
```

Events emitted by providers while streaming an assistant message.

### Event Type Guards

```python
from tinyagent.agent_types import (
    is_agent_end_event,
    is_turn_end_event,
    is_message_start_or_update_event,
    is_message_event,
    is_tool_execution_start_event,
    is_tool_execution_end_event,
    is_tool_execution_event,
)
```

Use these helpers in event handlers to keep discriminated event branching explicit and
avoid ad-hoc `getattr`/dict probing.

### AgentStartEvent / AgentEndEvent

```python
@dataclass
class AgentStartEvent:
    type: Literal["agent_start"] = "agent_start"

@dataclass
class AgentEndEvent:
    type: Literal["agent_end"] = "agent_end"
    messages: list[AgentMessage] = field(default_factory=list)
```

### TurnStartEvent / TurnEndEvent

```python
@dataclass
class TurnStartEvent:
    type: Literal["turn_start"] = "turn_start"

@dataclass
class TurnEndEvent:
    type: Literal["turn_end"] = "turn_end"
    message: AgentMessage | None = None
    tool_results: list[ToolResultMessage] = field(default_factory=list)
```

### MessageStartEvent / MessageUpdateEvent / MessageEndEvent

```python
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
```

### ToolExecution Events

```python
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
```

### Event Type Alias

```python
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
```

## Configuration Types

### AgentLoopConfig

```python
type ConvertToLlmFn = Callable[[list[AgentMessage]], MaybeAwaitable[list[Message]]]
type TransformContextFn = Callable[[list[AgentMessage], asyncio.Event | None], Awaitable[list[AgentMessage]]]
type ApiKeyResolver = Callable[[str], MaybeAwaitable[str | None]]
type AgentMessageProvider = Callable[[], Awaitable[list[AgentMessage]]]

@dataclass
class AgentLoopConfig:
    model: Model
    convert_to_llm: ConvertToLlmFn
    transform_context: TransformContextFn | None = None
    get_api_key: ApiKeyResolver | None = None
    get_steering_messages: AgentMessageProvider | None = None
    get_follow_up_messages: AgentMessageProvider | None = None
    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
```

### AgentState

```python
class AgentState(BaseModel):
    system_prompt: str = ""
    model: Model | None = None
    thinking_level: ThinkingLevel = ThinkingLevel.OFF
    tools: list[AgentTool] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    is_streaming: bool = False
    stream_message: AgentMessage | None = None
    pending_tool_calls: set[str] = Field(default_factory=set)
    error: str | None = None
```

## Protocol Types

### StreamFn

```python
type StreamFn = Callable[[Model, Context, SimpleStreamOptions], Awaitable["StreamResponse"]]
```

### StreamResponse

```python
class StreamResponse(Protocol):
    def result(self) -> Awaitable[AssistantMessage]: ...
    def __aiter__(self) -> AsyncIterator[AssistantMessageEvent]: ...
    async def __anext__(self) -> AssistantMessageEvent: ...
```

## Utility Types

### Model serialization contract

```python
from typing import Protocol

@runtime_checkable
class ModelDumpable(Protocol):
    def model_dump(self, *, exclude_none: bool = True) -> dict[str, object]: ...


def dump_model_dumpable(value: object, *, where: str) -> dict[str, object]:
    ...
```

`dump_model_dumpable` is the shared boundary helper used by providers to require
model-like payloads and fail fast when a message/event/model object does not follow
`model_dump()` contract.

### JsonValue / JsonObject

```python
JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
```

### EventStream

```python
class EventStream:
    def __init__(
        self,
        is_end_event: Callable[[AgentEvent], bool],
        get_result: Callable[[AgentEvent], list[AgentMessage]],
    )

    def push(self, event: AgentEvent) -> None
    def end(self, result: list[AgentMessage]) -> None
    async def result(self) -> list[AgentMessage]
```

Async event stream that yields events and returns a final result.
