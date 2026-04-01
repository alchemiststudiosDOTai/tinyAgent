# AGENTS.md

## Project
- This repo is now a Rust rewrite focused on a typed seam with `alchemy-rs`.
- Do not plan or implement against the old Python package layout. It is gone from this branch on purpose.
- Primary goal: a fully typed Rust agent/runtime layer that converts explicitly to and from the vendored `alchemy-llm` crate.

## Where To Start
- `rust/Cargo.toml` — active crate manifest for this branch.
- `rust/src/lib.rs` — current public Rust surface.
- `rust/src/types.rs` — runtime types owned by this repo.
- `rust/src/agent.rs` — typed agent/state layer.
- `rust/src/alchemy_contract.rs` — typed boundary to `vendor/alchemy-llm`.
- `docs/rust-runtime-types.md` — inventory of runtime types in `rust/src/types.rs`.
- `vendor/alchemy-llm/src/types/` — upstream typed alchemy message/model/event contracts.
- `vendor/alchemy-llm/src/stream/mod.rs` — generic typed stream dispatch.

## Repository Map
- `rust/`
  - `Cargo.toml` — crate config.
  - `src/lib.rs` — crate exports.
  - `src/types.rs` — runtime message, event, tool, context, and state types.
  - `src/agent.rs` — agent state management and event reduction.
  - `src/alchemy_contract.rs` — runtime/alchemy typed conversions and request builders.
- `docs/rust-runtime-types.md` — compact runtime type index.
- `vendor/alchemy-llm/` — vendored upstream crate used as the typed provider boundary.

## Commands
- `cargo test --manifest-path rust/Cargo.toml`
- `cargo test --manifest-path rust/Cargo.toml agent::tests`
- `cargo test --manifest-path rust/Cargo.toml alchemy_contract::tests`
- `cargo test --manifest-path vendor/alchemy-llm/Cargo.toml`

## Rewrite Rules
- Rust only. Do not reintroduce Python adapters, Python compatibility plans, or Python-first abstractions.
- Keep the seam typed end-to-end. Prefer `Model<TApi>`, typed options, typed messages, and typed events over string dispatch.
- Do not widen runtime enums or payloads “for compatibility” unless the wider shape is proven necessary and documented in code.
- If two typed models disagree, resolve it structurally:
  either tighten our type to match `alchemy-llm`, or introduce a separate explicit transport type.
- Do not hide type mismatches behind runtime fallback logic, silent coercion, or vague compatibility helpers.
- No stringly “api/provider logic” when the alchemy crate already expresses the distinction in types.
- No silent defaulting of required typed fields. Missing required data must stay impossible by construction, or fail explicitly at the boundary.
- No `unwrap()` or `expect()` in production paths. If one is truly unavoidable, justify it in a short code comment right there.
- No hidden lossy conversions. Any lossy bridge must be obvious in type names and function names.
- Prefer compile-time guarantees over runtime branching.

## Boundaries
- `rust/src/types.rs` is our runtime surface.
- `vendor/alchemy-llm/src/types/*.rs` is the upstream alchemy transport/model surface.
- `rust/src/alchemy_contract.rs` is the only place that should translate between those two domains.
- `rust/src/agent.rs` should depend on our runtime types, not on provider-specific internals from `vendor/alchemy-llm`.
- Loop execution and tool execution can arrive later; do not fake them with placeholders that blur the type boundary.

## Change Guardrails
- Before changing a contract type, inspect both `rust/src/types.rs` and the matching file under `vendor/alchemy-llm/src/types/`.
- When adding a new alchemy-facing capability, encode it as a typed builder or typed conversion first.
- Keep exported names in `rust/src/lib.rs` aligned with the actual crate surface.
- Add tests for every boundary rule you add in `rust/src/alchemy_contract.rs`.
- Keep `AGENTS.md` aligned with the repo that actually exists on this branch; remove stale paths aggressively.

## Validation Checklist
- Every path listed above exists.
- New runtime/alchemy conversions are covered by unit tests.
- `cargo test --manifest-path rust/Cargo.toml` passes after every meaningful change.
- If vendored alchemy types are touched, run `cargo test --manifest-path vendor/alchemy-llm/Cargo.toml`.
- No new Python-oriented guidance, files, or assumptions were added.
