# One Runtime Tool-Call Shape

This rewrite has exactly one runtime tool-call shape:
`ToolCallContent` in `rust/src/types.rs`.

That is the only tool-call structure the runtime should read, write, store, stream, or execute.

## Runtime Rule

The runtime-owned tool-call type is:

- `rust/src/types.rs` -> `ToolCallContent`

It carries the runtime fields the agent needs:

- `id`
- `name`
- `arguments`
- `partial_json`

The runtime uses that shape consistently across:

- `AssistantContent::ToolCall`
- `AssistantEventContent::ToolCall`
- `AssistantMessageEvent.tool_call`
- `agent_tool_execution.rs`
- agent state reduction in `agent.rs`

If code in the runtime needs a tool call, it should accept or produce `ToolCallContent`.
It should not introduce an OpenAI-specific, Anthropic-specific, or MiniMax-specific tool-call type.

## Provider Rule

Provider wire formats are not runtime shapes.

`vendor/alchemy-llm/` may use provider-native or OpenAI-compatible payloads such as `tool_calls`.
That is transport detail.
It stays below the runtime boundary.

The runtime should never depend on:

- OpenAI wire JSON field names
- provider-specific delta chunk layouts
- provider-specific function-call structs
- ad hoc `serde_json::Value` walking of provider tool-call payloads

## Boundary Rule

`rust/src/alchemy_backend.rs` is the only translation seam between:

- runtime-owned types in `rust/src/types.rs`
- vendored transport/provider types in `vendor/alchemy-llm/`

That file is allowed to translate:

- `ToolCallContent` -> vendored `ToolCall`
- vendored `ToolCall` -> `ToolCallContent`

Outside that file, runtime code should act as if provider wire formats do not exist.

## What This Means For MiniMax

MiniMax may arrive through an OpenAI-compatible transport path inside `alchemy-llm`.
That does not make the runtime an OpenAI tool-call runtime.

The runtime still sees one shape:
`ToolCallContent`.

So the clean mental model is:

1. Provider emits provider-specific tool-call payloads.
2. `alchemy-llm` parses them.
3. `rust/src/alchemy_backend.rs` converts them into `ToolCallContent`.
4. The runtime executes tools against `ToolCallContent`.

## Non-Goals

This doc does not require the vendored transport layer to share the runtime type.
The transport layer can keep its own typed provider contracts.

The rule is narrower and stricter:

- one runtime tool-call shape
- one translation seam
- zero provider-specific tool-call logic in runtime orchestration

## Review Standard

A tool-call-related change is correct only if all of the following remain true:

1. Runtime code still uses `ToolCallContent` as the canonical shape.
2. New provider-specific parsing stays in `vendor/alchemy-llm/` or `rust/src/alchemy_backend.rs`.
3. No second runtime tool-call struct is introduced.
4. No runtime module outside `rust/src/alchemy_backend.rs` learns provider wire details.
