---
title: "rust rewrite context synthesis research findings"
link: "rust-rewrite-context-synthesis-research"
type: research
ontological_relations:
  - relates_to: [[docs/ARCHITECTURE.md]]
  - relates_to: [[docs/releasing-alchemy-binding.md]]
  - relates_to: [[HARNESS.md]]
tags: [research, rust-binding, architecture, tinyagent]
uuid: "262C6037-3ED1-4982-AB08-6AC6CAA3E3DD"
created_at: "2026-03-30T21:04:51-05:00"
---

## Types

- Architecture policy makes type safety and message-boundary separation explicit: `docs/ARCHITECTURE.md:7`, `docs/ARCHITECTURE.md:9`, `docs/ARCHITECTURE.md:10`.
- The leaf type module defines the shared runtime contract surface used by both provider paths and the loop:
  - JSON/value helpers and `ZERO_USAGE`: `tinyagent/agent_types.py:18`, `tinyagent/agent_types.py:25`
  - `dump_model_dumpable(...)`: `tinyagent/agent_types.py:61`
  - message/content models: `tinyagent/agent_types.py:101`, `tinyagent/agent_types.py:118`, `tinyagent/agent_types.py:127`, `tinyagent/agent_types.py:142`, `tinyagent/agent_types.py:173`, `tinyagent/agent_types.py:187`
  - `Context`, `AgentContext`, `Model`, `SimpleStreamOptions`: `tinyagent/agent_types.py:259`, `tinyagent/agent_types.py:268`, `tinyagent/agent_types.py:277`, `tinyagent/agent_types.py:286`
  - `AssistantMessageEvent` and `StreamResponse`: `tinyagent/agent_types.py:298`, `tinyagent/agent_types.py:343`
  - agent lifecycle/tool events and `AgentState`: `tinyagent/agent_types.py:358`, `tinyagent/agent_types.py:400`, `tinyagent/agent_types.py:426`, `tinyagent/agent_types.py:481`, `tinyagent/agent_types.py:496`
- Import-boundary enforcement makes `agent_types.py` the governed leaf and places both binding adapters above it in the same layer: `tests/architecture/test_import_boundaries.py:30`, `tests/architecture/test_import_boundaries.py:33`, `tests/architecture/test_import_boundaries.py:41`, `tests/architecture/test_import_boundaries.py:76`.
- The public package surface re-exports types from `agent_types` at the root package, but does not re-export provider modules or provider-specific models/functions:
  - root imports and `__all__`: `tinyagent/__init__.py:6`, `tinyagent/__init__.py:19`, `tinyagent/__init__.py:57`, `tinyagent/__init__.py:60`
  - `ARCH003` enforces that `__init__.py` imports only configured core modules: `scripts/lint_architecture.py:13`, `scripts/lint_architecture.py:102`
  - configured `core_modules` exclude `alchemy_provider` and `rust_binding_provider`: `pyproject.toml:88`
- API docs match that split: root imports are shown for core types, while provider usage is imported from `tinyagent.alchemy_provider`: `docs/api/README.md:36`, `docs/api/README.md:39`, `docs/api/README.md:51`.

## Contracts

- The architecture doc defines the internal/external message boundary as `AgentMessage` to `Message` via `convert_to_llm()`: `docs/ARCHITECTURE.md:156`, `docs/ARCHITECTURE.md:170`.
- The loop implements that boundary in `_build_llm_context(...)`, transforming `AgentContext.messages` into `Context.messages` immediately before the provider call: `tinyagent/agent_loop.py:87`, `tinyagent/agent_loop.py:98`, `tinyagent/agent_loop.py:100`, `tinyagent/agent_loop.py:192`, `tinyagent/agent_loop.py:203`.
- The compatibility binding adapter imports only shared types from `agent_types`, validates returned assistant messages and `usage`, and serializes `model/context/options` dict payloads for `openai_completions_stream(...)`:
  - imports from `agent_types`: `tinyagent/alchemy_provider.py:22`
  - usage contract validation: `tinyagent/alchemy_provider.py:71`
  - assistant message validation: `tinyagent/alchemy_provider.py:92`
  - binding import path resolution: `tinyagent/alchemy_provider.py:111`
  - payload assembly and binding call: `tinyagent/alchemy_provider.py:293`, `tinyagent/alchemy_provider.py:305`, `tinyagent/alchemy_provider.py:313`, `tinyagent/alchemy_provider.py:319`
- The typed binding adapter defines explicit payload models around the same shared `Model`, `Context`, `SimpleStreamOptions`, and `AssistantMessageEvent` contracts:
  - module purpose: `tinyagent/rust_binding_provider.py:1`
  - `RustBindingModel`: `tinyagent/rust_binding_provider.py:78`
  - `BindingModelPayload`, `BindingToolPayload`, `BindingContextPayload`, `BindingOptionsPayload`: `tinyagent/rust_binding_provider.py:111`, `tinyagent/rust_binding_provider.py:123`, `tinyagent/rust_binding_provider.py:129`, `tinyagent/rust_binding_provider.py:135`
  - payload builders: `tinyagent/rust_binding_provider.py:298`, `tinyagent/rust_binding_provider.py:328`, `tinyagent/rust_binding_provider.py:349`
  - binding call with `model_dump(exclude_none=True)`: `tinyagent/rust_binding_provider.py:357`, `tinyagent/rust_binding_provider.py:369`
- The usage contract is documented separately and points back to the compatibility adapter and tests:
  - canonical usage doc and ontology links: `docs/api/usage-semantics.md:2`, `docs/api/usage-semantics.md:6`, `docs/api/usage-semantics.md:9`
  - canonical `AssistantMessage.usage` shape: `docs/api/usage-semantics.md:24`
  - runtime validation statement: `docs/api/usage-semantics.md:21`, `docs/api/usage-semantics.md:84`
- Contract tests pin both directions of the Python/native boundary:
  - compatibility provider forwards full payload and enforces `usage`: `tests/test_usage_contracts.py:144`
  - compatibility provider rejects missing `usage`: `tests/test_usage_contracts.py:335`
  - compatibility provider rejects non-`model_dump` messages: `tests/test_alchemy_provider.py:183`, `tests/test_alchemy_provider.py:202`
  - typed provider serializes explicit payloads: `tests/test_rust_binding_provider.py:145`
  - typed provider rejects legacy API alias and non-`model_dump` messages: `tests/test_rust_binding_provider.py:52`, `tests/test_rust_binding_provider.py:187`

## Components

- The enforced dependency order is:
  - layer 0 `agent_types`: `tests/architecture/test_import_boundaries.py:41`
  - layer 1 `agent_tool_execution`, `alchemy_provider`, `rust_binding_provider`, `proxy_event_handlers`, `caching`: `tests/architecture/test_import_boundaries.py:33`
  - layer 2 `agent_loop`, `proxy`: `tests/architecture/test_import_boundaries.py:32`
  - layer 3 `agent`: `tests/architecture/test_import_boundaries.py:31`
- Source imports match the enforced layering:
  - `alchemy_provider` imports from `agent_types` only: `tinyagent/alchemy_provider.py:22`
  - `rust_binding_provider` imports from `agent_types` only: `tinyagent/rust_binding_provider.py:19`
  - `agent_tool_execution` imports from `agent_types` only: `tinyagent/agent_tool_execution.py:11`
  - `agent_loop` imports `execute_tool_calls` plus `agent_types`: `tinyagent/agent_loop.py:13`, `tinyagent/agent_loop.py:14`
  - `agent` imports `agent_loop`, `agent_types`, and `caching`: `tinyagent/agent.py:10`, `tinyagent/agent.py:11`, `tinyagent/agent.py:40`
  - `proxy` imports `agent_types` and `proxy_event_handlers`: `tinyagent/proxy.py:19`, `tinyagent/proxy.py:30`
- The documented event flow is provider -> loop -> agent -> application: `docs/ARCHITECTURE.md:176`.
- The code path matches that flow:
  - provider responses yield `AssistantMessageEvent`: `tinyagent/alchemy_provider.py:179`, `tinyagent/rust_binding_provider.py:232`, `tinyagent/proxy.py:180`
  - loop converts stream events into `MessageStartEvent`, `MessageUpdateEvent`, `MessageEndEvent`, `TurnEndEvent`: `tinyagent/agent_loop.py:137`, `tinyagent/agent_loop.py:147`, `tinyagent/agent_loop.py:161`, `tinyagent/agent_loop.py:299`
  - tool execution converts `ToolCallContent` into `ToolExecutionStartEvent`, `ToolExecutionUpdateEvent`, `ToolExecutionEndEvent`, and `ToolResultMessage`: `tinyagent/agent_tool_execution.py:54`, `tinyagent/agent_tool_execution.py:116`, `tinyagent/agent_tool_execution.py:164`, `tinyagent/agent_tool_execution.py:198`, `tinyagent/agent_tool_execution.py:206`
  - `Agent` updates `AgentState` from those events: `tinyagent/agent.py:43`, `tinyagent/agent.py:55`, `tinyagent/agent.py:78`, `tinyagent/agent.py:89`, `tinyagent/agent.py:100`, `tinyagent/agent.py:141`
- The release/build workflow for `tinyagent._alchemy` is connected directly to packaging and distribution:
  - package-data includes `_alchemy` binaries: `pyproject.toml:50`
  - wheel purity flips to platform-specific when a staged `_alchemy` binary exists: `setup.py:8`, `setup.py:11`, `setup.py:19`
  - release doc defines the in-repo `rust/` build -> stage into `tinyagent/` -> check -> build -> repair -> smoke-test flow: `docs/releasing-alchemy-binding.md:9`, `docs/releasing-alchemy-binding.md:64`, `docs/releasing-alchemy-binding.md:83`, `docs/releasing-alchemy-binding.md:96`, `docs/releasing-alchemy-binding.md:111`, `docs/releasing-alchemy-binding.md:131`, `docs/releasing-alchemy-binding.md:145`, `docs/releasing-alchemy-binding.md:229`
  - workflow implements the same per-platform staging and validation:
    - Linux build/stage/check/smoke: `.github/workflows/publish-pypi.yml:44`, `.github/workflows/publish-pypi.yml:45`, `.github/workflows/publish-pypi.yml:48`, `.github/workflows/publish-pypi.yml:54`, `.github/workflows/publish-pypi.yml:55`
    - macOS build/stage/check/smoke: `.github/workflows/publish-pypi.yml:91`, `.github/workflows/publish-pypi.yml:93`, `.github/workflows/publish-pypi.yml:102`, `.github/workflows/publish-pypi.yml:111`, `.github/workflows/publish-pypi.yml:115`
    - Windows build/stage/check/smoke: `.github/workflows/publish-pypi.yml:148`, `.github/workflows/publish-pypi.yml:153`, `.github/workflows/publish-pypi.yml:155`, `.github/workflows/publish-pypi.yml:164`, `.github/workflows/publish-pypi.yml:169`
- Repository text currently contains both compatibility/external-binding wording and in-repo-restoration wording:
  - in-repo binding wording: `README.md:11`, `README.md:75`, `README.md:164`, `docs/releasing-alchemy-binding.md:9`, `HARNESS.md:30`, `AGENTS.md:3`, `AGENTS.md:73`, `tinyagent/rust_binding_provider.py:1`
  - external-binding wording: `docs/ARCHITECTURE.md:136`, `docs/api/providers.md:8`, `scripts/check_release_binding.py:4`, `scripts/check_release_binding.py:91`, `docs/harness/tool_call_types_harness.py:7`

## Testing

- Repo-level enforcement ties architecture and release rules into the harness system:
  - architecture doc says checks are blocking: `docs/ARCHITECTURE.md:247`
  - repo HARNESS lists `archlint`, `layer-lock`, `mypy`, `vulture`, `duplicate-code`, `debtlint`, `treelint`, and release checks: `HARNESS.md:5`, `HARNESS.md:13`, `HARNESS.md:14`, `HARNESS.md:29`, `HARNESS.md:31`, `HARNESS.md:34`
  - pre-commit config wires those hooks to concrete commands: `.pre-commit-config.yaml:26`, `.pre-commit-config.yaml:33`, `.pre-commit-config.yaml:40`, `.pre-commit-config.yaml:48`, `.pre-commit-config.yaml:56`, `.pre-commit-config.yaml:64`, `.pre-commit-config.yaml:71`, `.pre-commit-config.yaml:78`
- Type and event contracts are covered at multiple layers:
  - event guard and `EventStream` behavior: `tests/test_agent_types.py:102`, `tests/test_agent_types.py:128`, `tests/test_agent_types.py:152`, `tests/test_agent_types.py:160`
  - message roles, stop reasons, proxy-event guards, and tool-argument normalization: `tests/test_contracts.py:27`, `tests/test_contracts.py:59`, `tests/test_contracts.py:80`, `tests/test_contracts.py:102`, `tests/test_contracts.py:121`
  - compatibility provider helper behavior: `tests/test_alchemy_provider.py:28`, `tests/test_alchemy_provider.py:49`, `tests/test_alchemy_provider.py:64`, `tests/test_alchemy_provider.py:99`, `tests/test_alchemy_provider.py:183`
  - typed provider helper behavior: `tests/test_rust_binding_provider.py:30`, `tests/test_rust_binding_provider.py:40`, `tests/test_rust_binding_provider.py:52`, `tests/test_rust_binding_provider.py:145`
  - end-to-end usage payload preservation through `Agent`: `tests/test_usage_contracts.py:144`, `tests/test_usage_contracts.py:350`
- The live harness is a separate typed cutover proof path:
  - API docs point to it for runtime cutover validation: `docs/api/README.md:115`
  - harness script performs one real tool-calling turn through `tinyagent.alchemy_provider`, records assistant-stream event types, agent event types, message types, and content types, and prints only type names: `docs/harness/tool_call_types_harness.py:2`, `docs/harness/tool_call_types_harness.py:19`, `docs/harness/tool_call_types_harness.py:35`, `docs/harness/tool_call_types_harness.py:152`, `docs/harness/tool_call_types_harness.py:172`, `docs/harness/tool_call_types_harness.py:234`
  - live harness test is opt-in and asserts the expected output prefixes plus `result_type=AssistantMessage`: `tests/test_tool_call_types_harness.py:25`, `tests/test_tool_call_types_harness.py:32`, `tests/test_tool_call_types_harness.py:55`, `tests/test_tool_call_types_harness.py:70`
  - harness rules forbid duck-typed access and thin `Protocol` contracts inside `docs/harness/`: `docs/harness/HARNESS.md:13`, `docs/harness/HARNESS.md:18`, `rules/harness_no_duck_typing.yml:1`, `rules/harness_no_duck_typing.yml:8`, `rules/harness_no_thin_protocols.yml:1`, `rules/harness_no_thin_protocols.yml:7`
- Release/build validation has dedicated tests and scripts:
  - release binding checks: `scripts/check_release_binding.py:71`, `tests/test_release_binding.py:22`, `tests/test_release_binding.py:33`, `tests/test_release_binding.py:61`
  - wheel-tag checks: `scripts/check_release_wheels.py:67`, `tests/test_release_wheels.py:33`, `tests/test_release_wheels.py:45`
  - clean-venv wheel smoke test imports `tinyagent._alchemy`: `scripts/smoke_test_built_wheel.py:28`, `scripts/smoke_test_built_wheel.py:37`
  - release debug artifact captures wheel metadata and release-check output: `scripts/build_release_debug_artifact.py:80`, `tests/test_release_debug_artifact.py:38`
  - legacy wheel-to-package staging is still scripted and tested, but the release doc marks it as legacy and not used by the current in-repo release path: `scripts/stage_release_binding.py:53`, `tests/test_stage_release_binding.py:20`, `docs/releasing-alchemy-binding.md:37`
