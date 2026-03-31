# Rust Type Inventory

Rust runtime type definitions live in `rust/src/types.rs`.
The shape of these types follows `tinyagent/agent_types.py`.

## JSON and shared value types

- `JsonPrimitive`
- `JsonValue`
- `JsonObject`
- `UsagePayload`
- `CostPayload`
- `ThinkingBudgets`
- `ThinkingLevel`
- `StopReason`
- `STOP_REASONS`
- `STREAM_UPDATE_EVENTS`
- `zero_usage()`

## Content block types

- `CacheControl`
- `TextContent`
- `ImageContent`
- `ThinkingContent`
- `ToolCallContent`
- `ToolCall`
- `AssistantContent`
- `UserContent`
- `ToolResultContent`
- `AssistantEventContent`
- `AssistantEventError`

## Message types

- `UserMessage`
- `AssistantMessage`
- `ToolResultMessage`
- `CustomAgentMessage`
- `Message`
- `AgentMessage`

## Tool types

- `AgentToolResult`
- `AgentToolUpdateCallback`
- `AgentToolExecuteFn`
- `Tool`
- `AgentTool`

## Context and model types

- `MaybeAwaitable<T>`
- `ConvertToLlmFn`
- `TransformContextFn`
- `ApiKeyResolver`
- `AgentMessageProvider`
- `Context`
- `AgentContext`
- `Model`
- `SimpleStreamOptions`
- `StreamResponse`
- `StreamFn`

## Assistant stream event types

- `AssistantMessageEventType`
- `AssistantMessageEvent`

## Agent event types

- `AgentStartEventType`
- `AgentEndEventType`
- `TurnStartEventType`
- `TurnEndEventType`
- `MessageStartEventType`
- `MessageUpdateEventType`
- `MessageEndEventType`
- `ToolExecutionStartEventType`
- `ToolExecutionUpdateEventType`
- `ToolExecutionEndEventType`
- `AgentStartEvent`
- `AgentEndEvent`
- `TurnStartEvent`
- `TurnEndEvent`
- `MessageStartEvent`
- `MessageUpdateEvent`
- `MessageEndEvent`
- `ToolExecutionStartEvent`
- `ToolExecutionUpdateEvent`
- `ToolExecutionEndEvent`
- `MessageEvent`
- `ToolExecutionEvent`
- `AgentEvent`

## Loop, state, and stream types

- `AgentLoopConfig`
- `AgentState`
- `WakeupSignal`
- `EventStreamQueueItem`
- `EventStreamMessageError`
- `EventStreamError`
- `EventStream`
- `event_stream_error()`

## Event predicate functions

- `is_agent_end_event()`
- `is_turn_end_event()`
- `is_message_start_or_update_event()`
- `is_message_end_event()`
- `is_message_event()`
- `is_tool_execution_start_event()`
- `is_tool_execution_end_event()`
- `is_tool_execution_event()`
