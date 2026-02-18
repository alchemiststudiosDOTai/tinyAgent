---
title: Usage Semantics Alignment Plan (Option A: Provider-Raw)
link: usage-semantics-alignment-plan-provider-raw
type: doc
path: docs/plans/usage-semantics-alignment-plan.md
depth: 2
seams: [D]
ontological_relations:
  - relates_to: [[usage-contract]]
  - affects: [[tinyagent/openrouter_provider.py]]
  - affects: [[tinyagent/alchemy_provider.py]]
  - affects: [[src/lib.rs]]
  - affects: [[alchemy-rs/src/providers/openai_completions.rs]]
tags:
  - usage
  - contracts
  - openrouter
  - alchemy-rs
created_at: 2026-02-12T12:02:41-06:00
updated_at: 2026-02-12T12:02:41-06:00
uuid: 595275be-4cd1-43b6-98a3-6d8489104472
---

# Summary

Adopt **Option A (provider-raw semantics)** for usage fields so Python and Rust paths report the same meaning and the same contract shape.

Primary objective: if provider reports `usage`, we preserve that meaning without reinterpretation.

# Decision

Use **provider-raw semantics** for the usage contract:

- `input`: provider prompt tokens (`prompt_tokens`)
- `output`: provider completion tokens (`completion_tokens`)
- `cache_read`: provider cache-hit tokens (prefer explicit cache-read fields; fallback to `prompt_tokens_details.cached_tokens`)
- `cache_write`: provider cache-write tokens (prefer explicit cache-write fields; fallback to details)
- `total_tokens`: provider `total_tokens` when present; fallback `input + output`
- `cost`: keep current zero/default structure until real cost mapping is designed

Do **not** fold `reasoning_tokens` into `output`.

# Current Mismatch Map

## Python path (`tinyagent/openrouter_provider.py`)

Current behavior is already close to provider-raw:

- uses `prompt_tokens` for `input`
- uses `completion_tokens` for `output`
- reads cache fields from both Anthropic-style and OpenAI-style variants
- computes `total_tokens` as `input + output` (should prefer provider `total_tokens` first)

## Rust path (`alchemy-rs/src/providers/openai_completions.rs`)

Current behavior is normalized/billable style, not provider-raw:

- `input = prompt_tokens - cached_tokens`
- `output = completion_tokens + reasoning_tokens`
- `cache_write = 0` hardcoded
- `total_tokens = input + output + cache_read`

This causes drift vs Python and can diverge from provider `total_tokens`.

## Overflow utility (`alchemy-rs/src/utils/overflow.rs`)

Current silent-overflow check uses `input + cache_read`, assuming `input` is uncached-only.
If we switch to provider-raw (`input = prompt_tokens`), this check must be updated to avoid double-counting.

# Plan of Record

## Phase 0 — Freeze baseline (no behavior change)

1. Keep captured fixtures from live runs:
   - `data/rust_binding_full_run.json`
   - `data/python_provider_full_run.json`
2. Add one synthetic fixture containing:
   - `prompt_tokens`
   - `completion_tokens`
   - `total_tokens`
   - `prompt_tokens_details.cached_tokens`
   - `completion_tokens_details.reasoning_tokens`
   - optional cache write fields

## Phase 1 — Update `alchemy-rs` usage parsing to provider-raw

In `alchemy-rs/src/providers/openai_completions.rs`:

1. Extend `StreamUsage` to parse optional fields used by OpenRouter variants:
   - `total_tokens`
   - `cache_read_input_tokens`
   - `cache_creation_input_tokens`
2. Extend `PromptTokensDetails` with optional `cache_write_tokens`.
3. Replace `update_usage_from_chunk` logic with provider-raw mapping:
   - `input = prompt_tokens`
   - `output = completion_tokens`
   - `cache_read = first_non_zero(cache_read_input_tokens, prompt_tokens_details.cached_tokens, 0)`
   - `cache_write = first_non_zero(cache_creation_input_tokens, prompt_tokens_details.cache_write_tokens, 0)`
   - `total_tokens = usage.total_tokens.unwrap_or(input + output)`
4. Keep reasoning extraction for content streaming, but **do not add reasoning tokens into usage.output**.

## Phase 2 — Align tinyagent Rust binding integration

1. Ensure tinyagent build consumes the updated `alchemy-llm` behavior (path patch or dependency bump).
2. Confirm `src/lib.rs` needs no semantic change beyond pass-through (it already serializes `Usage` fields directly).
3. Rebuild binding and run contract tests.

## Phase 3 — Harden Python provider parity

In `tinyagent/openrouter_provider.py`:

1. Keep current cache-field parsing strategy.
2. Update `total_tokens` mapping to prefer provider `usage.total_tokens` when numeric, otherwise fallback `input + output`.
3. Keep `output = completion_tokens` (no reasoning-token folding).

## Phase 4 — Test matrix

1. Unit tests:
   - Python `_build_usage_dict`: all combinations of cache fields + `total_tokens` present/missing.
   - Rust usage parser tests for same combinations.
2. Contract tests (existing + new):
   - validate key presence and shape on both provider paths.
   - validate semantic expectations for fixture-driven cases.
3. Live parity smoke:
   - run Python and Rust paths with nonce prompts.
   - assert identical key sets and valid semantics (values may differ by upstream route).

## Phase 5 — Docs + release hygiene

1. Update docs to snake_case usage examples (`cache_read`, `cache_write`, `total_tokens`).
2. Add a short “Usage semantics” section clarifying provider-raw behavior.
3. Add changelog entry calling out semantics alignment (not just shape).

# Acceptance Criteria

1. Both Python and Rust paths return the same usage key set and same field meaning.
2. For fixtures containing provider `total_tokens`, output `usage.total_tokens` matches provider value.
3. `output` no longer increases with `reasoning_tokens` in Rust path.
4. `cache_write` is populated when provider reports it.
5. Contract tests + live smoke checks pass.

# Task Breakdown

## A. `alchemy-rs` changes

- [ ] A1: Extend `StreamUsage` + detail structs with optional fields.
- [ ] A2: Rewrite `update_usage_from_chunk` to provider-raw mapping.
- [ ] A3: Update/adjust overflow utility to avoid `input + cache_read` double-counting under provider-raw.
- [ ] A4: Add parser unit tests for mixed usage payload variants.

## B. tinyagent integration changes

- [ ] B1: Consume updated `alchemy-llm` in tinyagent build (path patch or bump).
- [ ] B2: Rebuild Rust binding and run `tests/test_usage_contracts.py`.
- [ ] B3: Confirm full suite remains green.

## C. Python provider parity changes

- [ ] C1: Prefer provider `total_tokens` when available.
- [ ] C2: Keep cache-read/cache-write fallback parsing and add coverage.

## D. Verification + docs

- [ ] D1: Re-run full real captures for Rust + Python.
- [ ] D2: Diff resulting payload semantics and archive outputs in `data/`.
- [ ] D3: Update docs examples and changelog.

# Notes / Non-Goals

- This plan does **not** introduce real cost computation.
- This plan does **not** force numeric equality between Python and Rust live runs (different upstream routing can change token counts).
- This plan focuses on semantic consistency of fields and predictable contract behavior.
