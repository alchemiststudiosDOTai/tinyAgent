# Data Ingress and Contract Confirmation

This document explains how data enters the runtime, where contracts are confirmed, and what evidence currently proves those contracts hold.

## Ingress Surfaces

There are four ingress paths that matter in this rewrite.

1. User input enters the runtime through `AgentInput`.
2. Runtime requests cross into `alchemy_llm` through `rust/src/alchemy_backend.rs`.
3. Provider responses and stream events come back from `alchemy_llm` through the same backend.
4. Assistant tool calls enter tool execution through `rust/src/agent_tool_execution.rs`.

Each path has a different confirmation point.

## Contract Table

| Ingress surface | Incoming shape | Confirmation point | Failure mode |
| --- | --- | --- | --- |
| User prompt ingress | `AgentInput` text, message, or messages | `Agent::build_input_messages` in `rust/src/agent.rs` | shape is normalized there; deeper provider and tool invariants are enforced later at their own boundaries |
| Runtime model ingress to backend | runtime `Model` | `AlchemyBackend::ensure_runtime_model_matches` | `ApiMismatch`, `ProviderMismatch`, `ModelIdMismatch` |
| Runtime context ingress to backend | runtime `Context` | `TryIntoAlchemy` impls in `rust/src/alchemy_backend.rs` | `MissingField`, `UnknownApi`, image/data URL errors, object-shape errors |
| Provider message ingress from alchemy | alchemy typed messages | `TryFromAlchemy` impls in `rust/src/alchemy_backend.rs` | explicit `AlchemyContractError` variants |
| Provider event ingress from alchemy | alchemy typed stream events | `TryFromAlchemy<AlchemyAssistantMessageEvent>` | explicit conversion failure, then backend emits runtime assistant error |
| Tool-call ingress | assistant tool-call blocks | `extract_tool_calls` and `executable_tool_call` in `rust/src/agent_tool_execution.rs` | `MissingToolCallId`, `MissingToolCallName` |
| Assistant stream ordering ingress | runtime assistant events | `agent_loop::stream_assistant_response` | `MissingAssistantEventPartial`, `AssistantUpdateBeforeStart` |

## Outbound Contract Confirmation

When the runtime sends a request into `alchemy_llm`, the backend confirms:

- the runtime model agrees with the typed backend model
- required provider-facing fields exist before transport conversion
- tool call arguments are JSON objects
- tool result details are JSON objects
- user images are representable as data URLs
- assistant messages moving toward alchemy are fully hydrated with metadata the transport requires

This means the rewrite does not silently invent missing transport fields at the boundary.

## Inbound Contract Confirmation

When `alchemy_llm` sends data back, the backend confirms:

- alchemy usage maps into runtime `UsagePayload`
- alchemy stop reasons map into runtime `StopReason`
- alchemy user, assistant, and tool-result messages map into runtime message types
- alchemy stream events map into runtime `AssistantMessageEvent`

If the alchemy payload cannot be represented in runtime types, the backend returns an explicit contract error and turns that into a runtime assistant error message instead of hiding the mismatch.

## Tool Execution Contract Confirmation

Tool execution has its own ingress checks after the assistant response is already in runtime form.

Before a tool is executed:

- the content block must actually be a tool call
- the tool call must have an `id`
- the tool call must have a `name`
- arguments stay in `JsonObject`

Once the tool is accepted for execution:

- the runtime emits `ToolExecutionStart`
- tool results are produced concurrently
- partial tool updates emit `ToolExecutionUpdate`
- the finalized result emits `ToolExecutionEnd`
- the result is converted into a typed `ToolResultMessage`

## Failure Semantics

The main boundary errors currently documented in code are:

- `MissingField`
- `ApiMismatch`
- `ProviderMismatch`
- `ModelIdMismatch`
- `UnknownApi`
- `ToolCallArgumentsMustBeObject`
- `ToolResultDetailsMustBeObject`
- `UnsupportedImageUrl`
- `UnsupportedAssistantContent`
- `InvalidDataUrl`
- `InvalidBase64Image`
- `MissingToolCallId`
- `MissingToolCallName`
- `MissingAssistantEventPartial`
- `AssistantUpdateBeforeStart`

The important point is that these are explicit contract failures.
They are not hidden by fallback logic.

## Proof in Unit Tests

The current crate test suite already exercises the main boundary rules.

### Backend conversion proof

- `usage_round_trip_matches_alchemy_shape`
- `stop_reason_round_trip_matches_alchemy_variants`
- `build_model_requires_typed_match`
- `build_model_rejects_provider_mismatch`
- `openai_options_derive_reasoning_effort_from_runtime_model`
- `user_message_image_round_trip_uses_data_urls`
- `assistant_message_requires_hydrated_metadata`
- `assistant_message_event_done_maps_to_runtime_event`
- `build_request_converts_context_tools_and_messages`
- `tool_call_arguments_must_be_objects`

### Runtime type proof

- `assistant_message_event_serializes_snake_case_type`
- `assistant_event_content_accepts_string_delta`
- `stop_reason_serializes_tool_use`
- `event_type_guards_cover_all_variants`
- `event_stream_yields_queued_event_before_end`
- `event_stream_raises_exception_after_draining_existing_events`
- `event_stream_result_propagates_exception`
- `event_stream_result_from_agent_end_event`

### Agent proof

- `builds_text_input_with_images`
- `extracts_text_from_supported_messages`
- `handle_events_updates_state`
- `records_turn_end_error_message`
- `meaningful_content_detects_text_thinking_and_tool_calls`
- `create_error_message_sets_stop_reason_and_usage`

## Proof in the Real Example

The live example in `rust/examples/minimax_agent_multiturn.rs` proves more than just conversion.
It proves:

- the runtime agent can call a real typed backend
- the model can issue real tool calls
- the tool execution layer runs
- multi-turn conversation state is preserved
- the second turn can refer to the first turn's result

The example enforces all of that by checking:

- at least 2 tool calls occurred
- turn 1 contains `56088`
- turn 2 contains `56098`

## Operator Validation Commands

Use these commands when checking ingress and boundary behavior on this branch:

```bash
cargo test --manifest-path rust/Cargo.toml
```

```bash
CARGO_HUSKY_DONT_INSTALL_HOOKS=1 cargo run --manifest-path rust/Cargo.toml --example minimax_agent_multiturn
```

The second command requires a valid `MINIMAX_API_KEY` in the environment.
