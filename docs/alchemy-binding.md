# Alchemy Binding Integration

This document is the single source of truth for TinyAgent's optional Rust-backed
alchemy integration.

It answers:

- where the binding lives
- what remains in this repo
- how runtime calls flow across the Python/Rust boundary
- how release wheels can include a built binding artifact
- which files and tests define the contract

## Scope and ownership

The Rust binding implementation is not maintained in this repository.

The source of truth for the binding implementation, build steps, and low-level
native API is:

- `https://github.com/tunahorse/tinyagent-alchemy`

This repository keeps only the Python-side compatibility layer and packaging
glue that let TinyAgent use a prebuilt binding artifact.

## What lives where

### External repo

Active ownership:

- Rust binding implementation
- native build instructions
- low-level exported `_alchemy` module behavior

Repo:

- `https://github.com/tunahorse/tinyagent-alchemy`

### This repo

Python/package responsibilities:

- `tinyagent/alchemy_provider.py`
  - Python adapter for the optional `tinyagent._alchemy` module
  - request serialization
  - provider/api/base_url/api-key resolution
  - streamed event validation
  - final message usage-contract validation
- `docs/releasing-alchemy-binding.md`
  - release-wheel staging workflow for a prebuilt `_alchemy` binary
- `tests/test_alchemy_provider.py`
  - adapter behavior and import/runtime validation
- `tests/test_usage_contracts.py`
  - payload-forwarding and usage-contract validation

## Runtime flow

The runtime path is:

`Agent -> stream_alchemy_openai_completions -> tinyagent._alchemy -> streamed events -> agent_loop -> Agent state/app`

### 1. Agent configuration

Applications opt into the binding-backed path by setting:

- `AgentOptions(stream_fn=stream_alchemy_openai_completions)`
- `OpenAICompatModel(...)`

The app does not call the Rust binding directly in normal TinyAgent usage.

### 2. Python resolves the binding module

`tinyagent.alchemy_provider._get_alchemy_module()` imports, in order:

1. `tinyagent._alchemy`
2. `_alchemy`

If neither import succeeds, TinyAgent raises a `RuntimeError` that points to the
external binding repo.

### 3. Python resolves request settings

`stream_alchemy_openai_completions()` resolves and normalizes:

- `provider`
- `api`
- `base_url`
- `api_key`
- optional model metadata such as `headers`, `reasoning`, `context_window`, and
  `max_tokens`

API selection rules:

- explicit `model.api` wins after alias normalization
- `provider in {"minimax", "minimax-cn"}` infers `minimax-completions`
- all other providers infer `openai-completions`

API key resolution order:

1. `options.api_key`
2. provider-specific env var fallback

Supported env vars:

- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `MINIMAX_API_KEY`
- `MINIMAX_CN_API_KEY`

### 4. Python serializes the request

The adapter builds three dict payloads and passes them over the Python/Rust
boundary:

- `model_dict`
- `context_dict`
- `options_dict`

`context_dict` includes:

- `system_prompt`
- serialized `messages`
- converted tool schemas

### 5. Python calls the Rust entrypoint

The adapter calls:

`tinyagent._alchemy.openai_completions_stream(model_dict, context_dict, options_dict)`

That returns a stream handle with:

- `next_event()`
- `result()`

### 6. Python consumes the native stream

`AlchemyStreamResponse` wraps the native handle and bridges it into TinyAgent's
async streaming contract.

Behavior:

- `__anext__()` calls `next_event()` via `asyncio.to_thread(...)`
- each returned event is validated as an `AssistantMessageEvent`
- `result()` calls the native `result()` method via `asyncio.to_thread(...)`
- the final assistant message is validated before being returned

This means the path is real-time, but the event iterator is not a native async
Rust stream exposed directly to Python. Python polls a blocking native method in
a worker thread.

### 7. TinyAgent continues with normal agent flow

After provider events come back from the binding-backed stream:

- `agent_loop` translates `AssistantMessageEvent` into `AgentEvent`
- tool calls are executed by TinyAgent's normal tool-execution path
- `Agent` updates state and forwards events to subscribers

The rest of the framework does not need special Rust-aware logic.

## Packaging and release flow

This repo does not build the binding from source.

If a release wheel should include `_alchemy`, the workflow is:

1. build the binding in the external repo
2. copy the built artifact into `tinyagent/`
3. run `python3 scripts/check_release_binding.py --require-present`
4. build the wheel
5. verify the wheel contains `tinyagent/_alchemy...`

Expected staged filenames include:

- `tinyagent/_alchemy.abi3.so`
- `tinyagent/_alchemy.<platform>.so`
- `tinyagent/_alchemy.pyd`
- `tinyagent/_alchemy.dylib`

The full release procedure remains documented in:

- [Shipping the `tinyagent._alchemy` Binding in Release Wheels](releasing-alchemy-binding.md)

## Current limitations

- only `openai-completions` and `minimax-completions` are dispatched
- image blocks are not supported yet
- streamed native events are consumed through blocking `next_event()` calls run
  in a worker thread

## Validation and enforcement

Primary code and test anchors:

- `tinyagent/alchemy_provider.py`
- `tests/test_alchemy_provider.py`
- `tests/test_usage_contracts.py`
- `docs/harness/tool_call_types_harness.py`

Useful validation commands:

```bash
uv run pytest tests/test_alchemy_provider.py tests/test_usage_contracts.py
uv run python docs/harness/tool_call_types_harness.py
```

## Related docs

- [Architecture](ARCHITECTURE.md)
- [API reference index](api/README.md)
- [Providers](api/providers.md)
- [OpenAI-compatible endpoints](api/openai-compatible-endpoints.md)
- [Usage semantics](api/usage-semantics.md)
- [Shipping the `tinyagent._alchemy` Binding in Release Wheels](releasing-alchemy-binding.md)
