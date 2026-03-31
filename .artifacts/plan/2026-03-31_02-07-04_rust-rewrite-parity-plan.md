---
title: "rust rewrite one-for-one parity implementation plan"
link: "rust-rewrite-parity-plan"
type: implementation_plan
ontological_relations:
  - relates_to: [[rust-rewrite-parity-synthesis-research]]
tags: [plan, rust-rewrite, parity, tinyagent]
uuid: "EAD28FFC-D564-4E94-A19A-4950650E6A4C"
created_at: "2026-03-31T02:07:04Z"
parent_research: ".artifacts/research/2026-03-31_02-07-04_rust-rewrite-parity-synthesis.md"
git_commit_at_plan: "2bda57b"
---

## Goal

- Rewrite the library in Rust while preserving one-for-one parity with the current Python package and binding behavior.
- Keep the Python-facing contract stable throughout the rewrite, especially `tinyagent.__init__`, `tinyagent._alchemy`, `tinyagent.alchemy_provider`, and `tinyagent.rust_binding_provider`.
- Execute work in this locked order only: `types -> contracts -> components -> testing`.

## Scope & Assumptions

- In scope: Rust-native equivalents for the current runtime type surface, provider/binding contracts, orchestration/runtime components, and parity validation.
- In scope: packaging and release flow needed to keep shipping `tinyagent._alchemy` from the in-repo crate.
- Out of scope: feature additions, API redesign, behavior cleanups, provider expansion, naming changes, and post-parity refactors.
- Assumption: the current Python modules, tests, docs, and release scripts are the source of truth until the Rust rewrite reaches parity.

## Deliverables

- A Rust-native implementation that preserves the current Python-visible runtime shapes and semantics.
- Stable Python adapters that continue to satisfy the existing `tinyagent._alchemy` contract.
- Release/build wiring that continues to stage, package, and smoke-test the in-repo binding.
- A parity validation pass that uses the existing test and harness surface as the acceptance bar.

## Readiness

- Source-of-truth modules: `tinyagent/agent_types.py`, `tinyagent/agent.py`, `tinyagent/agent_loop.py`, `tinyagent/agent_tool_execution.py`, `tinyagent/alchemy_provider.py`, `tinyagent/rust_binding_provider.py`, `tinyagent/proxy.py`, `tinyagent/proxy_event_handlers.py`, `tinyagent/caching.py`, `tinyagent/__init__.py`.
- Native binding entry point: `rust/src/lib.rs`, `rust/Cargo.toml`, `vendor/alchemy-llm/`.
- Architecture and release rules: `docs/ARCHITECTURE.md`, `docs/releasing-alchemy-binding.md`, `HARNESS.md`, `tests/architecture/test_import_boundaries.py`.
- Existing parity checks: `tests/`, `docs/harness/tool_call_types_harness.py`, `scripts/check_release_binding.py`, `scripts/check_release_wheels.py`.

## Milestones

- M1: Types parity
- M2: Contract parity
- M3: Component parity
- M4: Testing and cutover validation

## Phase Gates

- Do not start M2 until the shared Rust type surface matches the current Python-visible payload shapes.
- Do not start M3 until the provider, binding, proxy, and serialization contracts are stable against the current Python behavior.
- Do not start M4 until the Rust-backed components exist end to end.
- Reject any work item that introduces behavior drift before parity is established.

## Work Breakdown

### M1: Types parity

**T001**
- Summary: Mirror the current shared runtime type surface in Rust for JSON values, usage payloads, content blocks, messages, tool definitions, context/model/options, assistant stream events, agent events, agent state, and result-stream primitives.
- Dependencies: none
- Files/modules touched: `rust/src/lib.rs`, new Rust type modules under `rust/src/`, `vendor/alchemy-llm/src/types/` only if the existing vendored types cannot represent the Python source-of-truth shapes.
- Done when: every runtime shape presently defined in `tinyagent/agent_types.py` has a Rust representation with matching field names, optionality, and enum/literal values.

**T002**
- Summary: Preserve the Python package export contract while wiring the Rust type layer behind the binding boundary.
- Dependencies: T001
- Files/modules touched: `tinyagent/__init__.py`, `tinyagent/agent_types.py`, `tinyagent/alchemy_provider.py`, `tinyagent/rust_binding_provider.py`, `rust/src/lib.rs`.
- Done when: the root package surface and provider call sites still consume and return the same Python-visible shapes, with no export removals or renames.

### M2: Contract parity

**T003**
- Summary: Recreate the internal/external message boundary in Rust so `AgentMessage` to `Message`, `AgentContext` to `Context`, and final `AssistantMessage` return semantics stay identical to the current loop.
- Dependencies: T002
- Files/modules touched: `tinyagent/agent_loop.py`, `tinyagent/agent_types.py`, `rust/src/lib.rs`, new contract modules under `rust/src/`.
- Done when: the Rust-backed boundary preserves the current field filtering, message roles, stop reasons, and `usage` payload shape.

**T004**
- Summary: Preserve compatibility-provider and typed-binding payload construction, including provider resolution, API resolution, base URL resolution, API-key lookup, reasoning fields, and `tinyagent._alchemy` import behavior.
- Dependencies: T002
- Files/modules touched: `tinyagent/alchemy_provider.py`, `tinyagent/rust_binding_provider.py`, `rust/src/lib.rs`, `vendor/alchemy-llm/src/providers/`.
- Done when: both Python adapters still build the same payloads and accept the same returned payload contract as they do today.

**T005**
- Summary: Preserve proxy streaming contracts, including partial assistant mutation, tool-call JSON accumulation, stop-reason normalization, and error propagation.
- Dependencies: T003
- Files/modules touched: `tinyagent/proxy.py`, `tinyagent/proxy_event_handlers.py`, `rust/src/lib.rs`, new proxy contract modules under `rust/src/` if needed.
- Done when: the proxy path emits the same event types, content mutation sequence, and terminal message fields as the current implementation.

### M3: Component parity

**T006**
- Summary: Move stream/result mechanics into the Rust-backed path while preserving `EventStream` ordering, terminal result behavior, and exception propagation.
- Dependencies: T003
- Files/modules touched: `tinyagent/agent_types.py`, `tinyagent/agent_loop.py`, `rust/src/lib.rs`, new runtime stream modules under `rust/src/`.
- Done when: stream consumers observe the same event ordering and result/exception behavior currently enforced by `EventStream`.

**T007**
- Summary: Move tool execution semantics into the Rust-backed runtime while preserving concurrent execution, event ordering, tool-result ordering, and steering polling after the batch completes.
- Dependencies: T003
- Files/modules touched: `tinyagent/agent_tool_execution.py`, `tinyagent/agent_types.py`, `rust/src/lib.rs`, new tool execution modules under `rust/src/`.
- Done when: missing-tool, missing-execute, cancellation, error, and success paths produce the same event and `ToolResultMessage` outputs as the Python implementation.

**T008**
- Summary: Move the turn loop and agent orchestration semantics into the Rust-backed runtime while preserving prompt, continue, streaming, follow-up, steering, abort, and error flows.
- Dependencies: T006, T007
- Files/modules touched: `tinyagent/agent.py`, `tinyagent/agent_loop.py`, `tinyagent/caching.py`, `rust/src/lib.rs`, new loop/runtime modules under `rust/src/`.
- Done when: `Agent.prompt`, `prompt_text`, `stream`, `stream_text`, and `continue_` still exhibit the same externally visible behavior and state transitions.

**T009**
- Summary: Preserve binding packaging and release components for the in-repo Rust crate, including staging into `tinyagent/`, wheel classification, platform repair, and smoke imports of `tinyagent._alchemy`.
- Dependencies: T004, T008
- Files/modules touched: `pyproject.toml`, `setup.py`, `scripts/check_release_binding.py`, `scripts/check_release_wheels.py`, `scripts/smoke_test_built_wheel.py`, `.github/workflows/publish-pypi.yml`, `docs/releasing-alchemy-binding.md`, `HARNESS.md`.
- Done when: the in-repo binding can still be built, staged, packaged, and smoke-tested as the supported release path.

### M4: Testing and cutover validation

**T010**
- Summary: Re-run and update the existing parity suite in the order type/event tests, contract/provider tests, component-behavior tests, live harness checks, release checks, and architecture gates.
- Dependencies: T009
- Files/modules touched: `tests/test_agent_types.py`, `tests/test_contracts.py`, `tests/test_agent.py`, `tests/test_parallel_tool_execution.py`, `tests/test_alchemy_provider.py`, `tests/test_rust_binding_provider.py`, `tests/test_usage_contracts.py`, `tests/test_caching.py`, `tests/test_tool_call_types_harness.py`, `tests/test_release_binding.py`, `tests/test_stage_release_binding.py`, `tests/test_release_wheels.py`, `tests/test_release_debug_artifact.py`, `tests/architecture/test_import_boundaries.py`.
- Done when: the existing parity-focused tests pass against the Rust rewrite without relaxing the documented behavior.

**T011**
- Summary: Run the repo harness commands and align public docs with the final in-repo Rust ownership/build story after parity is confirmed.
- Dependencies: T010
- Files/modules touched: `README.md`, `docs/ARCHITECTURE.md`, `docs/api/README.md`, `docs/api/providers.md`, `docs/api/usage-semantics.md`, `docs/harness/tool_call_types_harness.py`, `HARNESS.md`, any script or doc still describing the old external split.
- Done when: documentation, harness text, and release instructions all describe the actual parity-preserving in-repo Rust implementation.

## Risks & Mitigations

- Risk: payload drift between Python models and native payloads.
  Mitigation: freeze parity against `tinyagent/agent_types.py`, provider adapters, and `tests/test_usage_contracts.py` before component work starts.
- Risk: layer violations while moving behavior behind Rust-backed modules.
  Mitigation: keep `tests/architecture/test_import_boundaries.py` as a standing gate and avoid bypassing the current module layering.
- Risk: release/build regressions for staged `_alchemy` wheels.
  Mitigation: keep `pyproject.toml`, `setup.py`, release scripts, and workflow changes inside the same parity scope as the binding rewrite.
- Risk: behavior drift in proxy/tool/event ordering.
  Mitigation: preserve `tests/test_parallel_tool_execution.py`, `tests/test_contracts.py`, `tests/test_proxy.py`, and the live harness as non-negotiable parity checks.

## Test Strategy

- Phase order stays locked, but the final acceptance bar is the existing repo harness and parity suite.
- Primary validation commands:
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

## References

- `.artifacts/research/2026-03-31_02-07-04_rust-rewrite-parity-synthesis.md`
- `.artifacts/research/2026-03-30_21-03-35_python-parity-map.md`
- `.artifacts/research/2026-03-30_21-04-34_rust-rewrite-locator.md`
- `.artifacts/research/2026-03-30_21-04-51_rust-rewrite-context-synthesis.md`
- `tinyagent/agent_types.py`
- `tinyagent/agent.py`
- `tinyagent/agent_loop.py`
- `tinyagent/agent_tool_execution.py`
- `tinyagent/alchemy_provider.py`
- `tinyagent/rust_binding_provider.py`
- `tinyagent/proxy.py`
- `tinyagent/proxy_event_handlers.py`
- `tinyagent/caching.py`
- `rust/src/lib.rs`
- `rust/Cargo.toml`
- `docs/ARCHITECTURE.md`
- `docs/releasing-alchemy-binding.md`
- `HARNESS.md`

## Final Gate

- Output summary: `.artifacts/plan/2026-03-31_02-07-04_rust-rewrite-parity-plan.md`
- Milestones: 4
- Tasks: 11
- Next step: execute the rewrite strictly in milestone order, stopping at each phase gate before moving to the next phase
