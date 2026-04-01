# Rust Runtime Types

`rust/src/types.rs` is the repo-owned runtime surface for the rewrite.
These types are what `Agent`, `agent_loop`, and `agent_tool_execution` work with directly.
They are not the vendored provider transport types. The provider bridge lives separately in `rust/src/alchemy_backend.rs`.

## Ownership Boundary

- Runtime surface: `rust/src/types.rs`
- Agent orchestration: `rust/src/agent.rs`, `rust/src/agent_loop.rs`, `rust/src/agent_tool_execution.rs`
- Provider transport surface: `vendor/alchemy-llm/src/types/*.rs`
- Runtime-to-provider translation: `rust/src/alchemy_backend.rs`

The main design rule is simple: agent code depends on these runtime types, not on `alchemy_llm` internals.

## Shared Value Types

- `JsonPrimitive`, `JsonValue`, and `JsonObject` are the shared JSON aliases used across messages, tools, and details payloads.
- `CostPayload` and `UsagePayload` model token accounting and cost accounting in the runtime layer.
- `StopReason` is a closed enum with the same effective stop set used by the alchemy transport:
  - `stop`
  - `length`
  - `tool_use`
  - `error`
  - `aborted`
- `ThinkingLevel` is the runtime control for reasoning depth. The backend later maps it to typed provider options.
- `ThinkingBudgets` carries optional runtime budget settings such as `thinking_budget` and `max_tokens`.

## Content Blocks

The runtime layer has three different content families because user input, assistant output, and tool results do not have the same legal shapes.

### User-side content

- `UserContent`
  - `Text(TextContent)`
  - `Image(ImageContent)`

### Assistant-side content

- `AssistantContent`
  - `Text(TextContent)`
  - `Thinking(ThinkingContent)`
  - `ToolCall(ToolCallContent)`

Assistant content is stored as `Vec<Option<AssistantContent>>` inside `AssistantMessage`.
That `Option` is deliberate: partial streaming state can exist before every block is fully materialized.

### Tool-result content

- `ToolResultContent`
  - `Text(TextContent)`
  - `Image(ImageContent)`

## Message Types

### Provider-facing runtime messages

- `UserMessage`
  - always has `role: user`
  - stores `Vec<UserContent>`
  - optional `timestamp`
- `AssistantMessage`
  - always has `role: assistant`
  - stores `Vec<Option<AssistantContent>>`
  - optional metadata in the runtime layer: `stop_reason`, `timestamp`, `api`, `provider`, `model`, `usage`, `error_message`
- `ToolResultMessage`
  - always has `role: tool_result`
  - carries `tool_call_id`, `tool_name`, `content`, `details`, `is_error`, `timestamp`

### Runtime envelope types

- `Message`
  - `User`
  - `Assistant`
  - `ToolResult`
- `AgentMessage`
  - `Message(Message)`
  - `Custom(CustomAgentMessage)`

`AgentMessage` exists so the runtime can keep local-only messages in state without forcing them across the provider boundary.
The default `convert_to_llm` path strips `Custom` messages before a provider request is built.

## Tools

There are two related but different tool types.

- `Tool`
  - transport-safe schema shape
  - `name`, `description`, `parameters`
- `AgentTool`
  - runtime shape
  - same transport fields plus `label`
  - optional executable closure in `execute`

`AgentTool.execute` is intentionally skipped by serde. The executable function is runtime-only and never crosses into provider transport.

`AgentToolResult` is the return shape from a tool execution:

- `content: Vec<ToolResultContent>`
- `details: JsonObject`

## Context, Model, and Stream Contracts

### Contexts

- `Context`
  - provider-facing runtime context
  - `system_prompt`
  - `messages: Vec<Message>`
  - optional `tools`
- `AgentContext`
  - agent-facing context
  - `system_prompt`
  - `messages: Vec<AgentMessage>`
  - optional `tools`

The loop converts `AgentContext` into `Context` by running:

1. optional `transform_context`
2. `convert_to_llm`

### Model

`Model` is the repo-owned runtime model descriptor:

- `provider`
- `id`
- `api`
- `thinking_level`

It is deliberately flat. The typed backend later confirms that this runtime descriptor matches the concrete typed alchemy model it wraps.

### Streaming

- `SimpleStreamOptions`
  - `api_key`
  - `temperature`
  - `max_tokens`
  - optional abort `signal`
- `StreamResponse`
  - `next_event()`
  - `result()`
- `StreamFn`
  - `Fn(Model, Context, SimpleStreamOptions) -> StreamResponse`

This is the main seam between the agent runtime and any backend implementation.

## Assistant Stream Events

`AssistantMessageEventType` is the runtime event set for provider streaming:

- `start`
- `text_start`
- `text_delta`
- `text_end`
- `thinking_start`
- `thinking_delta`
- `thinking_end`
- `tool_call_start`
- `tool_call_delta`
- `tool_call_end`
- `done`
- `error`

`AssistantMessageEvent` is the runtime event payload. It can carry:

- `partial`
- `content_index`
- `delta`
- `content`
- `tool_call`
- `reason`
- `message`
- `error`

This is the shape the backend emits and `agent_loop` consumes.

## Agent Events

The agent layer emits higher-level runtime events:

- `AgentStart`
- `AgentEnd`
- `TurnStart`
- `TurnEnd`
- `MessageStart`
- `MessageUpdate`
- `MessageEnd`
- `ToolExecutionStart`
- `ToolExecutionUpdate`
- `ToolExecutionEnd`

These events are the only thing listeners subscribe to on `Agent`.

## Loop and State Types

### `AgentLoopConfig`

This is the runtime execution contract for the loop:

- model
- conversion callbacks
- API key resolver
- steering/follow-up providers
- fallback API key
- temperature
- max tokens

### `AgentState`

This is the durable runtime state carried by `Agent`:

- `system_prompt`
- optional `model`
- `thinking_level`
- `tools`
- `messages`
- `is_streaming`
- `stream_message`
- `pending_tool_calls`
- optional `error`

### `EventStream`

`EventStream` is the agent runtime event queue:

- queues `AgentEvent`
- stores final result messages
- stores an explicit terminal exception
- wakes consumers through `Notify`
- returns queued events before surfacing terminal errors

This is how `agent_loop` publishes progress and how `Agent` consumes it.

## Runtime Invariants

- Only `rust/src/alchemy_backend.rs` should translate between runtime types and `alchemy_llm` types.
- `StopReason` is a closed, typed enum. No string stop-reason fallback exists in the runtime layer.
- Tool call arguments and tool result details are `JsonObject` in the runtime layer, not untyped JSON blobs.
- `AgentTool.execute` is runtime-only and never serialized.
- `AgentMessage::Custom` is allowed in runtime state but not sent to the provider by the default conversion path.
- `AgentState.pending_tool_calls` is driven only by typed tool execution events.

## Source Files

- `rust/src/types.rs`
- `rust/src/agent.rs`
- `rust/src/agent_loop.rs`
- `rust/src/agent_tool_execution.rs`
- `rust/src/alchemy_backend.rs`
