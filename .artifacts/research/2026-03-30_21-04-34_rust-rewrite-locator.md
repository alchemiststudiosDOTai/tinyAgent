---
title: "rust rewrite locator research findings"
link: "rust-rewrite-locator-research"
type: research
ontological_relations:
  - relates_to: [[docs/ARCHITECTURE.md]]
  - relates_to: [[docs/releasing-alchemy-binding.md]]
  - relates_to: [[docs/api/README.md]]
tags: [research, rust-rewrite, bindings]
uuid: "B0674720-AC8E-4097-A2FB-DD6E7AF2464E"
created_at: "2026-03-31T02:04:38Z"
---

## Structure
- Public Python package surface lives in `tinyagent/`.
- In-repo Rust binding crate lives in `rust/`.
- Vendored Rust dependency patched into the binding crate lives in `vendor/alchemy-llm/`.
- Release/build workflow lives in `pyproject.toml`, `setup.py`, `scripts/`, and `.github/workflows/publish-pypi.yml`.
- API/reference docs live in `docs/` and `docs/api/`.
- Test coverage lives in `tests/` and `tests/architecture/`.

## Phase 1: Types
- `tinyagent/__init__.py:6-58` imports the public Python symbols; `tinyagent/__init__.py:60-119` defines `__all__`.
- `tinyagent/agent_types.py:18-24` defines `JsonPrimitive`, `JsonValue`, `JsonObject`.
- `tinyagent/agent_types.py:72-77` defines `ThinkingBudgets`; `tinyagent/agent_types.py:84-92` defines `ThinkingLevel`.
- `tinyagent/agent_types.py:95-134` defines `CacheControl`, `TextContent`, `ImageContent`, `ThinkingContent`, `ToolCallContent`.
- `tinyagent/agent_types.py:137-139` aliases `ToolCall` and `AssistantContent`.
- `tinyagent/agent_types.py:142-199` defines `UserMessage`, `StopReason`, `AssistantMessage`, `ToolResultMessage`, `Message`.
- `tinyagent/agent_types.py:202-219` defines `CustomAgentMessage`, `AgentMessage`, and callback type aliases.
- `tinyagent/agent_types.py:226-252` defines `AgentToolResult`, `Tool`, `AgentTool`.
- `tinyagent/agent_types.py:260-293` defines `Context`, `AgentContext`, `Model`, `SimpleStreamOptions`.
- `tinyagent/agent_types.py:298-350` defines `AssistantMessageEvent` and `StreamResponse`.
- `tinyagent/agent_types.py:358-437` defines `AgentEvent` variants.
- `tinyagent/agent_types.py:481-518` defines `AgentLoopConfig`, `AgentState`, `EventStream`.
- `docs/api/agent_types.md:9-259` mirrors the Python runtime type surface in docs.
- `docs/diagrams/tinyagent-type-map.html:864-883` names the main runtime type groups; `docs/diagrams/tinyagent-type-map.html:1288-1308` summarizes the type map.
- `tests/test_agent_types.py:9-33` imports the event types and guards; `tests/test_agent_types.py:48-118` enumerates all agent event variants under test.
- `tests/test_contracts.py:5-16` imports runtime message/content/tool types; `tests/test_contracts.py:80-142` checks role literals, stop reasons, and tool-argument normalization.

## Phase 2: Contracts
- `tinyagent/alchemy_provider.py:37-49` defines the Python protocol for the `_alchemy` stream handle and binding entry point.
- `tinyagent/alchemy_provider.py:71-108` validates `usage` and assistant-message return payloads.
- `tinyagent/alchemy_provider.py:111-137` loads `_alchemy` via `_alchemy` or `tinyagent._alchemy`.
- `tinyagent/alchemy_provider.py:140-153` defines `OpenAICompatModel`.
- `tinyagent/alchemy_provider.py:190-202` serializes `AgentTool` into the binding payload.
- `tinyagent/alchemy_provider.py:205-253` resolves `base_url`, `provider`, and `api`.
- `tinyagent/alchemy_provider.py:256-266` resolves API keys from `SimpleStreamOptions` or environment.
- `tinyagent/alchemy_provider.py:269-325` is the compatibility stream entry point that forwards `model`, `context`, and `options` dict payloads into `_alchemy.openai_completions_stream(...)`.
- `tinyagent/rust_binding_provider.py:29-35` defines `BindingApi`, `ReasoningEffort`, `ReasoningMode`.
- `tinyagent/rust_binding_provider.py:37-53` defines provider default base URLs and env-key mapping.
- `tinyagent/rust_binding_provider.py:65-71` defines the typed `_alchemy` protocol.
- `tinyagent/rust_binding_provider.py:78-109` defines `RustBindingModel`.
- `tinyagent/rust_binding_provider.py:111-139` defines `BindingModelPayload`, `BindingToolPayload`, `BindingContextPayload`, `BindingOptionsPayload`.
- `tinyagent/rust_binding_provider.py:148-185` validates `usage` and assistant-message payloads.
- `tinyagent/rust_binding_provider.py:188-206` loads `tinyagent._alchemy` then `_alchemy`.
- `tinyagent/rust_binding_provider.py:241-295` resolves provider, API, base URL, and API key.
- `tinyagent/rust_binding_provider.py:298-354` builds typed model/context/options payloads.
- `tinyagent/rust_binding_provider.py:357-374` is the typed binding stream entry point.
- `tinyagent/proxy_event_handlers.py:23-42` parses streamed tool-argument JSON fragments.
- `tinyagent/proxy_event_handlers.py:81-84` normalizes stop reasons against `STOP_REASONS`.
- `tinyagent/proxy_event_handlers.py:87-335` maps proxy SSE event payloads into `AssistantMessageEvent`.
- `tinyagent/agent_tool_execution.py:29-31` defines `ToolExecutionResult`.
- `tinyagent/agent_tool_execution.py:34-52` normalizes tool-call arguments.
- `tinyagent/agent_tool_execution.py:164-218` executes tool calls and emits `ToolExecution*` plus `ToolResultMessage` contracts.
- `tinyagent/agent_loop.py:87-105` builds provider-facing `Context` from `AgentContext`.
- `tinyagent/agent_loop.py:117-126` coerces provider payloads to `AssistantMessage` / `AssistantMessageEvent`.
- `tinyagent/agent_loop.py:183-220` streams provider events through the loop contract.
- `docs/api/providers.md:17-75` documents `OpenAICompatModel`, `stream_alchemy_openai_completions`, and API-key resolution.
- `docs/api/openai-compatible-endpoints.md:22-63` documents `OpenAICompatModel.base_url`, API inference, and usage semantics.
- `docs/api/usage-semantics.md:16-43` defines the canonical `AssistantMessage.usage` shape; `docs/api/usage-semantics.md:58-84` defines field mapping and enforcement.
- `tests/test_alchemy_provider.py:17-25` imports the alchemy contract helpers; `tests/test_alchemy_provider.py:28-96` checks base URL, API, and API-key resolution; `tests/test_alchemy_provider.py:99-143` checks binding import fallback/error reporting; `tests/test_alchemy_provider.py:183-242` checks payload serialization requirements.
- `tests/test_rust_binding_provider.py:18-27` imports the typed binding helpers; `tests/test_rust_binding_provider.py:30-99` checks API/base URL/env-key resolution and typed payload serialization; `tests/test_rust_binding_provider.py:145-200` checks `stream_rust_binding`.
- `tests/test_usage_contracts.py:1-6` states the Rust/Python boundary invariants; `tests/test_usage_contracts.py:61-80` defines a fake `_alchemy` module; `tests/test_usage_contracts.py:115-141` defines the canonical usage payload; `tests/test_usage_contracts.py:144-225` checks forwarded model/context/options payloads and returned usage; `tests/test_usage_contracts.py:230-344` checks reasoning, API inference, explicit API override, and usage enforcement; `tests/test_usage_contracts.py:350-578` checks usage/tool metadata preservation through `Agent` and `agent_loop`.
- `tests/test_contracts.py:27-53` checks proxy type-guard contracts; `tests/test_contracts.py:59-74` checks proxy event index behavior.

## Phase 3: Components
- Public Python entry points:
  - `tinyagent/__init__.py:6-58`
  - `tinyagent/__init__.py:60-119`
- High-level agent:
  - `tinyagent/agent.py:256-269` defines `AgentOptions`
  - `tinyagent/agent.py:272-609` defines `Agent`
  - `tinyagent/agent.py:609-636` builds `AgentContext` and `AgentLoopConfig`
- Loop/orchestration:
  - `tinyagent/agent_loop.py:53-64` defines `create_agent_stream`
  - `tinyagent/agent_loop.py:183-220` defines `stream_assistant_response`
  - `tinyagent/agent_loop.py:314-365` defines `run_loop`
  - `tinyagent/agent_loop.py:368-407` defines `agent_loop`
  - `tinyagent/agent_loop.py:410-459` defines `agent_loop_continue`
- Proxy provider:
  - `tinyagent/proxy.py:33-42` defines `ProxyStreamOptions`
  - `tinyagent/proxy.py:74-115` builds the proxy request body
  - `tinyagent/proxy.py:166-269` defines `ProxyStreamResponse`
  - `tinyagent/proxy.py:272-301` defines `stream_proxy` and `create_proxy_stream`
  - `tinyagent/proxy.py:304-309` exports the proxy API via `__all__`
- Rust binding crate:
  - `rust/Cargo.toml:1-19` defines the `_alchemy` cdylib crate and patches `alchemy-llm` to `vendor/alchemy-llm`
  - `rust/src/lib.rs:90-237` defines Python-facing Rust input models (`PyModelInput`, `PyContextInput`, `PyMessageInput`, content enums, `PyToolInput`)
  - `rust/src/lib.rs:239-343` defines `StreamHandle`
  - `rust/src/lib.rs:345-389` defines the exposed `_alchemy.openai_completions_stream(...)`
  - `rust/src/lib.rs:585-639` converts Python messages into `alchemy_llm::types::Message`
  - `rust/src/lib.rs:642-730` converts Python content/options into Rust/provider inputs
  - `rust/src/lib.rs:733-880` converts Rust assistant messages and events back into Python JSON payloads
  - `rust/src/lib.rs:901-979` parses API/provider/stop reasons and tool-call arguments
  - `rust/src/lib.rs:1027-1031` registers the `_alchemy` Python module
- Vendored Rust library used by the binding:
  - `vendor/alchemy-llm/src/lib.rs:1-30` re-exports types, providers, stream entry points, and utilities
  - `vendor/alchemy-llm/src/types/mod.rs:1-34` re-exports the Rust-side shared type modules
  - `vendor/alchemy-llm/src/types/api.rs:7-160` defines `Api`, `KnownProvider`, `Provider`, and `ApiType`
  - `vendor/alchemy-llm/src/types/model.rs:15-117` defines Rust `Model<TApi>` and API marker types
  - `vendor/alchemy-llm/src/types/options.rs:4-86` defines `StreamOptions`, `SimpleStreamOptions`, `ThinkingLevel`, `ThinkingBudgets`
  - `vendor/alchemy-llm/src/types/content.rs:8-105` defines Rust-side content and tool-call payloads
  - `vendor/alchemy-llm/src/types/message.rs:9-94` defines Rust-side `Message`, `AssistantMessage`, `ToolResultMessage`, `Context`
  - `vendor/alchemy-llm/src/types/event.rs:6-92` defines Rust-side `AssistantMessageEvent`
  - `vendor/alchemy-llm/src/types/usage.rs:4-50` defines Rust-side `Usage`, `Cost`, `StopReason`
  - `vendor/alchemy-llm/src/providers/mod.rs:1-14` re-exports provider implementations
  - `vendor/alchemy-llm/src/providers/openai_completions.rs:22-101` defines `OpenAICompletionsOptions` and the OpenAI-compatible provider entry point
  - `vendor/alchemy-llm/src/providers/minimax.rs:32-323` defines the MiniMax provider entry point
  - `vendor/alchemy-llm/src/providers/kimi.rs:14-23` defines the Kimi provider entry point
  - `vendor/alchemy-llm/src/providers/anthropic.rs:14-...` defines the Anthropic provider entry point
  - `vendor/alchemy-llm/src/providers/env.rs:17-...` defines env-key lookup
  - `vendor/alchemy-llm/src/stream/mod.rs:23-125` dispatches stream requests across provider implementations

## Phase 4: Testing
- Type and event contracts:
  - `tests/test_agent_types.py:1-165`
  - `tests/test_contracts.py:1-142`
  - `tests/test_agent.py:1-86`
- Tool execution behavior:
  - `tests/test_parallel_tool_execution.py:10-315`
  - `docs/api/agent_tool_execution.md:7-163`
- Provider/binding contract coverage:
  - `tests/test_alchemy_provider.py:17-242`
  - `tests/test_rust_binding_provider.py:18-200`
  - `tests/test_usage_contracts.py:1-578`
  - `docs/harness/tool_call_types_harness.py:19-243`
  - `tests/test_tool_call_types_harness.py:25-51`
- Usage/caching contract coverage:
  - `tests/test_caching.py:18-226`
  - `docs/api/usage-semantics.md:95-112`
- Build/release contract coverage:
  - `tests/test_release_binding.py:6-94`
  - `tests/test_stage_release_binding.py:8-97`
  - `tests/test_release_wheels.py:6-70`
  - `tests/test_release_debug_artifact.py:7-82`
- Architecture boundary enforcement:
  - `tests/architecture/test_import_boundaries.py:30-55` defines the governed module layers
  - `tests/architecture/test_import_boundaries.py:63-99` enforces illegal import, leaf, and governance checks

## Build and Release Entry Points
- `pyproject.toml:1-3` sets the Python build backend.
- `pyproject.toml:47-52` includes `tinyagent` package data patterns for `_alchemy`.
- `setup.py:8-21` marks wheels as platform-specific when `_alchemy` is staged.
- `scripts/check_release_binding.py:20-40` locates staged `_alchemy` artifacts; `scripts/check_release_binding.py:71-107` enforces package-data and host-format checks.
- `scripts/stage_release_binding.py:53-69` stages a single `_alchemy` member from a wheel into `tinyagent/`.
- `scripts/smoke_test_built_wheel.py:28-38` installs a built wheel into a clean venv and imports `tinyagent._alchemy`.
- `.github/workflows/publish-pypi.yml:22-56` builds, stages, repairs, and smoke-tests the Linux wheel.
- `.github/workflows/publish-pypi.yml:85-115` builds, stages, and smoke-tests the macOS wheel.
- `.github/workflows/publish-pypi.yml:144-169` builds, stages, and smoke-tests the Windows wheel.
- `docs/releasing-alchemy-binding.md:60-237` documents the staged-binding release workflow.
- `HARNESS.md:27-37` records the release gates and workflow path.
