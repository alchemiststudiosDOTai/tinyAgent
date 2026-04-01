# Agent to Alchemy Backend Connection

This rewrite keeps the agent runtime and the provider backend separate.

- Agent/runtime layer: `rust/src/agent.rs`, `rust/src/agent_loop.rs`, `rust/src/agent_tool_execution.rs`
- Typed provider bridge: `rust/src/alchemy_backend.rs`
- Vendored provider engine: `vendor/alchemy-llm/`

The agent does not call `alchemy_llm` directly.
It talks to a backend through `StreamFn` and `StreamResponse`.
`AlchemyBackend` is the concrete implementation of that seam for the vendored alchemy crate.

## End-to-End Flow

1. `Agent::prompt`, `prompt_text`, or `continue_` starts a run.
2. `Agent` builds `AgentContext` from current `AgentState`.
3. `Agent` builds `AgentLoopConfig` with the runtime `Model`, conversion callbacks, and queue providers.
4. `agent_loop::build_llm_context` converts `AgentContext` into `Context`.
5. `agent_loop::resolve_api_key` chooses the key for the current provider.
6. `agent_loop::stream_assistant_response` calls the configured `StreamFn`.
7. `AlchemyBackend::stream_fn` wraps the typed alchemy backend as that `StreamFn`.
8. `AlchemyBackend::build_request` confirms runtime model identity and converts runtime `Context` into alchemy `Context`.
9. `alchemy_llm::stream(...)` runs the real provider request.
10. `AlchemyBackend` converts alchemy stream events into runtime `AssistantMessageEvent`.
11. `agent_loop` turns assistant stream events into runtime `AgentEvent` values.
12. `Agent::consume_stream` applies those events back into `AgentState`.

## Why the Seam Is `StreamFn`

The runtime only requires this contract:

- a runtime `Model`
- a runtime `Context`
- runtime `SimpleStreamOptions`
- a `StreamResponse` that yields typed assistant events and a final typed assistant message

That keeps the agent layer backend-agnostic while still staying fully typed.

## What `AlchemyBackend` Owns

`AlchemyBackend<TApi>` wraps a typed `alchemy_llm::types::Model<TApi>`.
It owns:

- the concrete typed provider model
- default provider options
- request building
- runtime-to-alchemy conversion
- alchemy-to-runtime conversion
- backend error normalization into runtime assistant error messages

It does not own agent state, tool execution, queueing, or turn control.

## Runtime Model Confirmation

`AlchemyBackend::ensure_runtime_model_matches` confirms that the runtime `Model` matches the typed backend model on:

- `api`
- `provider`
- `id`

This prevents a runtime agent from accidentally pairing one model description with a different typed backend model.

## Request Construction

`AlchemyBackend::build_request` produces an `AlchemyRequest<TApi>` with:

- `model: AlchemyModel<TApi>`
- `context: alchemy_llm::types::Context`
- `options: OpenAICompletionsOptions`

The request build has three checks:

1. runtime model identity must match the typed backend model
2. runtime `Context` must convert successfully into alchemy `Context`
3. runtime stream options must map cleanly into typed provider options

## Options Mapping

The backend maps runtime options into typed provider options.

- `api_key` passes through if present
- `temperature` passes through if present
- `max_tokens` passes through if present
- `thinking_level` maps to typed `ReasoningEffort` when the backend options do not already override it

That mapping is explicit in `build_openai_options(...)` and `AlchemyBackend::openai_options(...)`.

## Event Bridge

`alchemy_llm` yields typed `AssistantMessageEvent` enum values.
The backend converts each one into the repo-owned runtime `AssistantMessageEvent` struct.

The loop then reduces those runtime assistant events into higher-level runtime agent events:

- assistant `start` -> `MessageStart`
- assistant deltas -> `MessageUpdate`
- assistant `done` or `error` -> `MessageEnd`

This keeps streaming logic inside the agent runtime while keeping provider transport logic inside the backend.

## Error Behavior

The backend does not panic for request or conversion failures.
Instead it emits a typed runtime assistant error event and returns a final runtime `AssistantMessage` with:

- `stop_reason = error`
- runtime `api`, `provider`, and `model`
- zeroed usage
- `error_message`

That gives the agent layer a uniform failure surface even when the failure started inside provider transport.

## Boundary Rule

`rust/src/alchemy_backend.rs` is the only place that should know both:

- repo runtime types from `rust/src/types.rs`
- vendored transport types from `vendor/alchemy-llm/src/types/*.rs`

If new provider-facing behavior is added, the typed conversion or typed builder should be added here first.
