# Rust Binding Restoration

## Summary

This artifact records the work to bring the Rust binding back into this repo and
replace the stale external-style runtime path with an in-repo binding and a new
typed Python adapter.

## What Changed

### 1. New in-repo Rust crate

Added a Rust crate at:

- `rust/Cargo.toml`
- `rust/src/lib.rs`

The crate now:

- builds a Python extension module named `_alchemy`
- depends on `alchemy-llm`
- uses `pyo3` for the Python boundary
- exposes `openai_completions_stream(model, context, options)`

### 2. Fresh `_alchemy` extension contract

The Rust binding now accepts a typed JSON-shaped contract:

- `model`
  - `id`
  - `provider`
  - `api`
  - `base_url`
  - `name`
  - `headers`
  - `reasoning`
  - `context_window`
  - `max_tokens`
- `context`
  - `system_prompt`
  - `messages`
  - `tools`
- `options`
  - `api_key`
  - `temperature`
  - `max_tokens`

The Rust side maps upstream `alchemy-llm` events/messages into TinyAgent’s
Python-facing snake_case shape:

- event names like `text_delta`, `tool_call_end`, `done`
- content blocks like `text`, `thinking`, `tool_call`
- usage fields like `input`, `output`, `cache_read`, `cache_write`, `total_tokens`

### 3. New typed Python adapter

Added a new Python module at:

- `tinyagent/rust_binding_provider.py`

This module is separate from the legacy compatibility adapter in
`tinyagent/alchemy_provider.py`.

It provides:

- `RustBindingModel`
- `stream_rust_binding(...)`
- typed payload models for the Rust boundary
- strict API handling for:
  - `openai-completions`
  - `minimax-completions`
  - `anthropic-messages`

Notable provider behavior:

- `provider="kimi"` defaults to `api="anthropic-messages"`
- `provider in {"minimax", "minimax-cn"}` defaults to `api="minimax-completions"`
- other supported providers default to `api="openai-completions"`

### 4. Fresh binary installed in repo

The repo had an older compiled binary at:

- `tinyagent/_alchemy.abi3.so`

That file was stale and still enforced the older contract.

It was replaced with the freshly built binary from the new crate so Python now
imports the new in-repo binding implementation.

## Tests And Validation

### Rust tests

Ran:

```bash
cargo test
```

Result:

- all Rust contract tests passed

### Python unit and architecture tests

Ran:

```bash
uv run pytest tests/test_rust_binding_provider.py tests/architecture/test_import_boundaries.py -q
uv run ruff check tinyagent/rust_binding_provider.py tests/test_rust_binding_provider.py
uv run mypy --ignore-missing-imports tinyagent/rust_binding_provider.py tests/test_rust_binding_provider.py
```

Result:

- tests passed
- ruff passed
- mypy passed

## Live Provider Verification

### Direct binding checks

Verified through `tinyagent._alchemy`:

- MiniMax: passed
- Kimi: passed
- OpenAI: passed

### New typed adapter checks

Verified through `tinyagent.rust_binding_provider.stream_rust_binding(...)`:

- MiniMax: passed
- Kimi: passed
- OpenAI: passed

### OpenAI multi-turn tool calling

Verified with `gpt-4o-mini` through `Agent` plus `stream_rust_binding(...)`:

- multi-turn tool execution worked
- three tool calls were issued across turns:
  - `add`
  - `multiply`
  - `subtract`
- final answer was `38.0`

### OpenAI prompt caching

Observed behavior:

- short prompts showed `cache_read=0` and `cache_write=0`
- long repeated-prefix prompts on `gpt-4o-mini` did show cache hits

3-turn OpenAI result with a long repeated prefix:

- turn 1: `cache_read=0`
- turn 2: `cache_read=3840`
- turn 3: `cache_read=3840`

Conclusion:

- prompt caching works through the restored binding
- earlier zero-cache runs were due to prompt size / repeated-prefix size, not a binding failure

## Files Added Or Changed

- `rust/Cargo.toml`
- `rust/Cargo.lock`
- `rust/src/lib.rs`
- `tinyagent/rust_binding_provider.py`
- `tests/test_rust_binding_provider.py`
- `tests/architecture/test_import_boundaries.py`
- `tinyagent/_alchemy.abi3.so`

## Current State

The repo now has:

- an in-repo Rust binding crate
- a fresh compiled `_alchemy` extension in `tinyagent/`
- a new typed Python adapter for the restored contract
- successful live verification for OpenAI, MiniMax, and Kimi

The legacy compatibility adapter in `tinyagent/alchemy_provider.py` was not
rewritten as part of this step.
