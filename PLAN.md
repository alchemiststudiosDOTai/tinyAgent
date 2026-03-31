# Rust Rewrite Plan

## Goal

Rewrite TinyAgent in Rust with one-for-one parity to the current Python library. The rewrite order is locked:

1. Types
2. Contracts
3. Components
4. Testing

No feature work, API changes, renames, or behavior cleanup should happen before parity is complete.

## Non-Negotiables

- Keep the Python-facing contract stable while the implementation moves into Rust.
- Preserve `tinyagent.__init__`, `tinyagent._alchemy`, `tinyagent.alchemy_provider`, and `tinyagent.rust_binding_provider`.
- Treat the current Python modules, tests, docs, and release scripts as the source of truth until the Rust path matches them.
- Do not start a later phase until the current phase is complete.

## Source Of Truth

- Public/runtime types: `tinyagent/agent_types.py`, `tinyagent/__init__.py`
- High-level runtime: `tinyagent/agent.py`, `tinyagent/agent_loop.py`, `tinyagent/agent_tool_execution.py`
- Provider and binding contracts: `tinyagent/alchemy_provider.py`, `tinyagent/rust_binding_provider.py`, `tinyagent/proxy.py`, `tinyagent/proxy_event_handlers.py`, `tinyagent/caching.py`
- Native binding: `rust/src/lib.rs`, `rust/Cargo.toml`, `vendor/alchemy-llm/`
- Rules and architecture: `docs/ARCHITECTURE.md`, `docs/releasing-alchemy-binding.md`, `HARNESS.md`, `tests/architecture/test_import_boundaries.py`
- Acceptance surface: `tests/`, `docs/harness/tool_call_types_harness.py`, release scripts in `scripts/`

## Phase 1: Types

Start by mirroring the shared runtime type surface in Rust. This phase is about shapes only: JSON helpers, usage payloads, content blocks, messages, tool definitions, context/model/options, assistant stream events, agent events, agent state, and result-stream primitives.

The source of truth here is `tinyagent/agent_types.py`, with the public export surface anchored by `tinyagent/__init__.py`. The Rust side must also match the binding payload shapes already present in `rust/src/lib.rs` and the vendored type system in `vendor/alchemy-llm/`.

The implementation target for this phase is `rust/src/types.rs`. `rust/src/lib.rs` should only translate between Python payloads, the local Rust types, and `vendor/alchemy-llm/` types without inventing new shapes.

### Phase 1A: JSON helpers and constants

Mirror the base value layer first so every later struct can reuse the same shapes.

- `JsonPrimitive`, `JsonValue`, `JsonObject`
- zero-usage equivalent for `ZERO_USAGE`
- `StopReason` and `STOP_REASONS`
- `ThinkingLevel`
- `STREAM_UPDATE_EVENTS`

Requirements:

- Serialized field names and literal values must match Python exactly.
- The Rust default/constructor path for zero usage must preserve the current `usage` payload shape.
- Snake-case enum serialization must match the Python literals accepted today.

### Phase 1B: Content and message shapes

Build the content/message family next.

- `ThinkingBudgets`
- `CacheControl`
- `TextContent`
- `ImageContent`
- `ThinkingContent`
- `ToolCallContent` / `ToolCall`
- `AssistantContent`
- Rust-only helper unions for user/tool-result content payloads
- `UserMessage`
- `AssistantMessage`
- `ToolResultMessage`
- `CustomAgentMessage`
- `Message`
- `AgentMessage`

Requirements:

- `AssistantMessage.content` must remain `list[AssistantContent | None]` in shape, including `null` entries.
- `ToolCallContent.arguments` and `ToolResultMessage.details` must stay open JSON objects.
- `AssistantMessage.usage` must preserve the current Python-visible payload contract.
- Rust-side enums/unions must deserialize the same tagged payloads the Python models accept now.

### Phase 1C: Tool, context, and model shapes

Once the message layer is stable, add the shared runtime structs that wrap it.

- `AgentToolResult`
- `Tool`
- `AgentTool`
- `Context`
- `AgentContext`
- `Model`
- `SimpleStreamOptions`

Requirements:

- `AgentTool` in Rust is shape-only during this phase. Its callable `execute` path stays non-serialized and non-parity-blocking until contracts/components.
- Sensitive runtime fields such as `SimpleStreamOptions.api_key` should stay debuggable without leaking secrets.
- The Rust structs must preserve the fields the Python adapters already expect when they serialize/deserialize across the binding.

### Phase 1D: Assistant stream and agent event shapes

After the shared data models exist, mirror the event payloads exactly.

- `AssistantMessageEvent`
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
- `AgentEvent`
- `AgentState`
- wakeup/result-stream queue items used by the event stream implementation

Requirements:

- `AssistantMessageEvent.type` literals must match the current streaming contract exactly.
- `AssistantMessageEvent.content` and `AssistantMessageEvent.error` must remain permissive enough to carry the current Python payloads.
- `AgentState.pending_tool_calls` must preserve set semantics.
- Event structs must serialize to the same public payloads the Python runtime emits today.

### Phase 1E: Explicit deferrals

The following names live in `tinyagent/agent_types.py`, but they are not plain Rust data models and should not be treated as blockers for finishing the shape pass:

- `ModelDumpable`
- `dump_model_dumpable()`
- `MaybeAwaitable`
- `ConvertToLlmFn`
- `TransformContextFn`
- `ApiKeyResolver`
- `AgentMessageProvider`
- `AgentToolUpdateCallback`
- `StreamFn`
- `StreamResponse`
- type-guard helpers such as `is_agent_end_event()`
- the behavioral implementation of `EventStream`
- `AgentLoopConfig` because it is mostly callback contract, not stable serialized data

Those items belong to Phase 2 or Phase 3 unless a Rust-only helper is needed to support an already-approved shape in Phase 1.

### Phase 1 completion checklist

- Every Python-visible data shape in `tinyagent/agent_types.py` that crosses a binding or serialization boundary has a Rust equivalent in `rust/src/types.rs`.
- `rust/src/lib.rs` conversions use those local Rust types instead of ad hoc payload structs where practical.
- Serialization tests cover the literal/tagged cases that are easy to drift on: roles, content `type`, stop reasons, assistant event `type`, nullable assistant content entries, and zero-usage payloads.
- Nothing in this phase changes runtime control flow, provider selection, proxy behavior, or tool execution semantics.

Exit criteria:

- Rust-native representations exist for every Python-visible runtime shape that matters to the current library.
- Field names, optional fields, literal values, and export expectations match the current package.
- No contract or component behavior has been changed yet.

## Phase 2: Contracts

Once the types are fixed, rebuild the contracts around them. This phase covers the boundaries and invariants that make the library behave the way it does today.

That includes:

- `AgentMessage -> Message` and `AgentContext -> Context` conversion
- `AssistantMessageEvent` and final `AssistantMessage` return behavior
- `usage` payload requirements
- provider resolution, API resolution, base URL resolution, and API-key lookup
- `tinyagent._alchemy` import/load behavior
- proxy event parsing, stop-reason normalization, and tool-call partial JSON accumulation
- tool execution result shapes and event contracts

Exit criteria:

- The Rust-backed boundary produces and accepts the same payloads as the current Python adapters.
- The compatibility path and typed binding path both preserve the current contract.
- Proxy and tool-call contracts still match the current behavior.

## Phase 3: Components

After the contract layer is stable, move the runtime components behind it. Build the implementation from the lower-level pieces upward so the current architecture still makes sense during the rewrite.

Recommended component order inside this phase:

1. Stream/result mechanics
2. Tool execution engine
3. Turn loop/orchestration
4. Agent wrapper/state updates
5. Proxy and provider integration points
6. Packaging and release wiring for `tinyagent._alchemy`

The target is parity for:

- event ordering
- tool execution ordering
- steering and follow-up behavior
- abort/error behavior
- `prompt`, `prompt_text`, `stream`, `stream_text`, and `continue_`
- release/build flow that stages and ships the in-repo binding

Exit criteria:

- The Rust-backed runtime can cover the same end-to-end flows as the current Python implementation.
- The Python-facing package surface remains stable.
- The release path for staged `_alchemy` wheels still works.

## Phase 4: Testing

Testing is the final phase, not the starting point. Once the components exist, run the existing repo checks as the parity bar and only update tests where the rewrite requires it without changing behavior.

Validation order:

1. Type and event tests
2. Contract and provider tests
3. Component behavior tests
4. Live harness checks
5. Release/build checks
6. Architecture and lint gates

Core commands:

- `uv run pytest`
- `uv run mypy --ignore-missing-imports --exclude "lint_file_length\\.py$" .`
- `python3 scripts/lint_architecture.py`
- `.venv/bin/python -m pytest tests/architecture/test_import_boundaries.py -x -q`
- `uv run vulture --min-confidence 80 tinyagent`
- `uv run pylint --disable=all --enable=duplicate-code tinyagent`
- `python3 scripts/lint_debt.py`
- `python3 scripts/check_release_binding.py`
- `python3 scripts/check_release_binding.py --require-present`
- `uv run python docs/harness/tool_call_types_harness.py`

Exit criteria:

- Existing parity-focused tests and harness checks pass against the Rust rewrite.
- Architecture boundaries still hold.
- Release docs and build/release scripts describe the actual in-repo Rust path.

## Execution Rule

The rewrite does not move forward by module count or by “how much Rust was written.” It moves forward only by parity gates.

- Finish types before contracts.
- Finish contracts before components.
- Finish components before testing.
- If a change breaks one-for-one parity, stop and fix that drift before continuing.
