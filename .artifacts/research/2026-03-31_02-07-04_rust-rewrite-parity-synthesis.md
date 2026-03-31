---
title: "rust rewrite parity synthesis research findings"
link: "rust-rewrite-parity-synthesis-research"
type: research
ontological_relations:
  - relates_to: [[python-parity-map-research]]
  - relates_to: [[rust-rewrite-locator-research]]
  - relates_to: [[rust-rewrite-context-synthesis-research]]
  - relates_to: [[docs/ARCHITECTURE.md]]
  - relates_to: [[docs/releasing-alchemy-binding.md]]
tags: [research, rust-rewrite, parity, tinyagent]
uuid: "C7B078FB-98F8-442B-968B-2F9AF7241851"
created_at: "2026-03-31T02:07:04Z"
---

## Scope

- Research focus: a one-for-one Rust rewrite plan for this repo in the required order `types -> contracts -> components -> testing`.
- Git state during synthesis: commit `2bda57b` with a clean working tree.

## Types

- The governed leaf module is `tinyagent/agent_types.py`; it defines the shared Python runtime surface for JSON helpers, content/message models, tool/context/model types, stream events, lifecycle events, loop config, state, and `EventStream`.
- The public Python surface is re-exported from `tinyagent/__init__.py` and currently exposes core agent, loop, tool, type, and proxy symbols.
- The Rust binding crate lives at `rust/` with `_alchemy` exposed from `rust/src/lib.rs`; Python-facing Rust input/output shapes are defined there and the crate is packaged as a `cdylib` from `rust/Cargo.toml`.
- The vendored Rust dependency surface used by the binding lives under `vendor/alchemy-llm/src/types/` and `vendor/alchemy-llm/src/providers/`.
- Type documentation and type-map references live in `docs/api/agent_types.md` and `docs/diagrams/tinyagent-type-map.html`.

## Contracts

- The architecture boundary is `AgentContext` / `AgentMessage` internally and `Context` / `Message` at the provider boundary; the conversion happens in `tinyagent/agent_loop.py` immediately before the provider call.
- Both `tinyagent/alchemy_provider.py` and `tinyagent/rust_binding_provider.py` serialize shared Python models into payloads for `tinyagent._alchemy` and validate returned assistant messages plus `usage`.
- The compatibility binding path lives in `tinyagent/alchemy_provider.py`; the typed binding path lives in `tinyagent/rust_binding_provider.py`.
- Proxy streaming contracts are implemented in `tinyagent/proxy.py` and `tinyagent/proxy_event_handlers.py`, including partial event mutation, stop-reason normalization, and tool-call JSON accumulation.
- Tool execution contracts are implemented in `tinyagent/agent_tool_execution.py`, including concurrent execution, `ToolExecution*` events, and `ToolResultMessage` generation.
- Canonical provider and usage contract documentation lives in `docs/api/providers.md`, `docs/api/openai-compatible-endpoints.md`, and `docs/api/usage-semantics.md`.

## Components

- Enforced import layering is `agent` -> `agent_loop|proxy` -> `agent_tool_execution|alchemy_provider|rust_binding_provider|proxy_event_handlers|caching` -> `agent_types`.
- The high-level public wrapper is `tinyagent/agent.py`; loop/orchestration lives in `tinyagent/agent_loop.py`; caching lives in `tinyagent/caching.py`.
- The release/build path for `tinyagent._alchemy` is connected through `pyproject.toml`, `setup.py`, `scripts/check_release_binding.py`, `scripts/check_release_wheels.py`, `scripts/smoke_test_built_wheel.py`, and `.github/workflows/publish-pypi.yml`.
- The release workflow documentation for the in-repo binding lives in `docs/releasing-alchemy-binding.md` and is reinforced in `HARNESS.md`.
- Repo text currently contains both in-repo binding wording and older external-binding wording across docs and scripts.

## Testing

- Type and event behavior is covered in `tests/test_agent_types.py`, `tests/test_contracts.py`, and `tests/test_agent.py`.
- Tool execution behavior is covered in `tests/test_parallel_tool_execution.py`.
- Binding/provider contracts are covered in `tests/test_alchemy_provider.py`, `tests/test_rust_binding_provider.py`, and `tests/test_usage_contracts.py`.
- Caching behavior is covered in `tests/test_caching.py`.
- The live typed harness is `docs/harness/tool_call_types_harness.py` with coverage in `tests/test_tool_call_types_harness.py`.
- Release/build checks are covered in `tests/test_release_binding.py`, `tests/test_stage_release_binding.py`, `tests/test_release_wheels.py`, and `tests/test_release_debug_artifact.py`.
- Architecture governance is enforced in `tests/architecture/test_import_boundaries.py`, `scripts/lint_architecture.py`, `.pre-commit-config.yaml`, and `HARNESS.md`.

## Source Documents

- `.artifacts/research/2026-03-30_21-03-35_python-parity-map.md`
- `.artifacts/research/2026-03-30_21-04-34_rust-rewrite-locator.md`
- `.artifacts/research/2026-03-30_21-04-51_rust-rewrite-context-synthesis.md`
