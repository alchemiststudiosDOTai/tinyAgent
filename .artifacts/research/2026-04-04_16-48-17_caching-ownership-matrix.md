---
title: Caching Ownership Matrix
summary: Ownership split for the current prompt-caching failures and telemetry differences across TinyAgent, the in-repo Rust binding, and vendored alchemy-llm.
last_updated: "2026-04-04"
---

# Caching Ownership Matrix

## Scope

This matrix answers one question:

Who owns each part of the current caching behavior?

It is grounded in:

- real runtime artifacts
- current TinyAgent Python code
- current in-repo Rust binding code
- current vendored `alchemy-llm` code

## Matrix

| Symptom | Proof | Owning Layer | Exact Fix Location |
| --- | --- | --- | --- |
| Python creates `cache_control`, but provider path does not carry it | `.artifacts/runtime/openrouter_cache_debug_payload_2026-04-04.json` shows `python_context_has_cache_control = true`; `tinyagent/caching.py:22` sets it on user text blocks | Shared ownership: TinyAgent already creates it; Rust/alchemy path loses it | Primary fix starts in `vendor/alchemy-llm/src/types/content.rs:67` and `vendor/alchemy-llm/src/types/message.rs:30`, because the vendored model has no `cache_control` field on user text content |
| Rust binding drops `cache_control` before request construction | `rust/src/lib.rs:169` `PyUserContentInput::Text` only accepts `text`; `rust/src/lib.rs:642` forwards only `text` and `text_signature` | In-repo Rust binding | `rust/src/lib.rs:169` and `rust/src/lib.rs:642` |
| `session_id` exists conceptually but TinyAgent does not send it | `tinyagent/agent.py:294` stores `_session_id`; `.artifacts/runtime/openrouter_cache_debug_payload_2026-04-04.json` shows `session_id_forwarded_by_stream_options = false`; `tinyagent/agent_types.py:286` has no `session_id` on `SimpleStreamOptions` | TinyAgent integration | `tinyagent/agent_types.py:286`, `tinyagent/agent_loop.py:195`, and `tinyagent/alchemy_provider.py:313` |
| Vendored alchemy crate already has a place for `session_id` | `vendor/alchemy-llm/src/types/options.rs:14` exposes `session_id()` and `vendor/alchemy-llm/src/types/options.rs:59` stores `session_id` in `BaseStreamOptions` | Not an alchemy-crate gap for this field | No crate change required for the basic field; TinyAgent must pass it through |
| MiniMax reported cache reads while OpenRouter did not | `.artifacts/runtime/minimax_cache_probe_2026-04-04.json` shows `cache_read = 32`; `.artifacts/runtime/openrouter_gpt41mini_cache_probe_2026-04-04.json` shows `cache_read = 0` | Provider behavior / provider telemetry difference | No direct TinyAgent fix for the telemetry difference itself; TinyAgent can only surface what the provider returns |
| MiniMax path explicitly asks for usage and parses cache fields | `vendor/alchemy-llm/src/providers/minimax.rs:118` sets `stream_options.include_usage = true`; `vendor/alchemy-llm/src/providers/shared/stream_blocks.rs:63` parses `cache_read_input_tokens` and `cache_creation_input_tokens` | Vendored alchemy provider path already supports usage telemetry parsing | No fix needed here unless MiniMax request semantics themselves need to change |
| OpenRouter `gpt-4.1-mini` zero-cache run does not prove provider caching is impossible | `.artifacts/runtime/openrouter_gpt41mini_cache_probe_2026-04-04.json` only proves the observed run returned zeros | Residual uncertainty at provider/model level | After wiring `cache_control` and `session_id`, rerun probes to determine whether OpenRouter starts returning cache telemetry |

## Conclusions

### 1. `cache_control` is not just a TinyAgent bug

TinyAgent creates it correctly in Python.

The missing support is lower in the path:

- vendored `alchemy-llm` does not model user-text `cache_control`
- the in-repo Rust binding therefore does not deserialize or forward it

### 2. `session_id` is primarily a TinyAgent integration bug

The vendored crate already supports `session_id`.

TinyAgent does not currently thread it through:

- Python `Agent`
- `SimpleStreamOptions`
- provider adapter
- Rust binding options payload

### 3. MiniMax cache telemetry does not prove the explicit TinyAgent caching design works end to end

What it proves is narrower:

- MiniMax returned cache counters in usage
- TinyAgent/alchemy surfaced those counters

That can happen even while explicit `cache_control` and `session_id` wiring are still incomplete.

## Proof Bundle

- `.artifacts/research/2026-04-04_16-38-57_openrouter-cache-miss-proof.md`
- `.artifacts/runtime/openrouter_cache_debug_payload_2026-04-04.json`
- `.artifacts/runtime/openrouter_gpt41mini_cache_probe_2026-04-04.json`
- `.artifacts/runtime/minimax_cache_probe_2026-04-04.json`
