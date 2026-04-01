# AGENTS.md

## Project
- Rust rewrite only.
- `vendor/alchemy-llm/` is the typed provider backend, not the rewrite target.
- Primary goal: a typed agent/runtime layer that stays separate from the vendored transport layer.

## Start Here
- `rust/Cargo.toml` — active crate manifest.
- `rust/src/lib.rs` — exported crate surface.
- `rust/src/types.rs` — runtime-owned types.
- `rust/src/agent.rs` — `Agent`, state reduction, run lifecycle.
- `rust/src/agent_loop.rs` — turn loop and streaming reduction.
- `rust/src/agent_tool_execution.rs` — tool-call execution path.
- `rust/src/alchemy_backend.rs` — only runtime/alchemy translation layer.
- `rust/examples/minimax_agent_multiturn.rs` — real end-to-end example.
- `docs/README.md` — rewrite doc index.

## Repository Map
- `rust/src/types.rs` — messages, content blocks, events, tool types, loop config, state, stream queue.
- `rust/src/agent.rs` — runtime API: prompting, continuation, listeners, aborts, state updates.
- `rust/src/agent_loop.rs` — builds `Context`, resolves API key, drives turns, emits `AgentEvent`.
- `rust/src/agent_tool_execution.rs` — validates tool calls, runs tools, emits tool execution events.
- `rust/src/alchemy_backend.rs` — typed builders and `TryIntoAlchemy` / `TryFromAlchemy` conversions.
- `vendor/alchemy-llm/src/types/` — upstream typed transport contracts.
- `vendor/alchemy-llm/src/stream/mod.rs` — upstream streaming entrypoint.
- `docs/` — rewrite docs for types, backend seam, ingress contracts, and the real agent.

## Commands
- `cargo test --manifest-path rust/Cargo.toml`
- `cargo test --manifest-path rust/Cargo.toml agent::tests`
- `cargo test --manifest-path rust/Cargo.toml alchemy_backend::tests`
- `cargo run --manifest-path rust/Cargo.toml --example minimax_agent_multiturn`
- `cargo test --manifest-path vendor/alchemy-llm/Cargo.toml`

## Rewrite Rules
- Rust only. Do not reintroduce Python code, compatibility layers, or Python-first docs.
- Keep the seam typed end to end. Prefer typed models, typed events, typed builders, and typed conversions.
- `rust/src/alchemy_backend.rs` is the only place that should translate to or from `vendor/alchemy-llm`.
- Do not hide type mismatches behind fallback logic, silent coercion, or vague compatibility helpers.
- No stringly provider dispatch when `alchemy-llm` already expresses the distinction in types.
- No ad hoc `serde_json::Value` walking in core logic when a typed struct or enum should exist.
- No `dict/get` style Rust design.
- No silent defaulting of required boundary data.
- No `unwrap()` or `expect()` in production paths.
- Avoid `panic!` and “should never happen” branches in runtime code. Return explicit errors instead.
- Prefer compile-time guarantees over runtime branching.

## Boundaries
- Runtime surface: `rust/src/types.rs`
- Agent/runtime orchestration: `rust/src/agent.rs`, `rust/src/agent_loop.rs`, `rust/src/agent_tool_execution.rs`
- Provider boundary: `rust/src/alchemy_backend.rs`
- Vendored transport surface: `vendor/alchemy-llm/src/types/*.rs`

## Docs
- `docs/rust-runtime-types.md`
- `docs/rust-agent-alchemy-backend.md`
- `docs/rust-data-ingress-contracts.md`
- `docs/rust-real-agent.md`

## Validation Checklist
- Every path listed above exists.
- New boundary rules in `rust/src/alchemy_backend.rs` have unit-test coverage.
- `cargo test --manifest-path rust/Cargo.toml` passes after meaningful code changes.
- If `vendor/alchemy-llm` types are touched, run `cargo test --manifest-path vendor/alchemy-llm/Cargo.toml`.
- Keep this file aligned with the branch that actually exists.
