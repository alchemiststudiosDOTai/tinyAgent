---
title: OpenAI-Compatible Endpoints via OpenRouterModel
description: Use OpenRouterModel.base_url to target OpenAI-compatible /chat/completions endpoints (OpenRouter, OpenAI, Chutes, local servers) without custom HTTP wrappers.
ontological_relations:
  - extends: providers.md#OpenRouter-Provider
  - extends: providers.md#Alchemy-Provider
  - implemented_by: ../../tinyagent/openrouter_provider.py
  - implemented_by: ../../tinyagent/alchemy_provider.py
  - validated_by: ../../tests/test_openrouter_provider.py
  - validated_by: ../../tests/test_alchemy_provider.py
  - composes_with: agent.md#AgentOptions
---

# OpenAI-Compatible Endpoints via `OpenRouterModel.base_url`

## Summary

TinyAgent’s native OpenRouter model config supports a `base_url` override on `OpenRouterModel`.
You can use this with both provider paths:

- `stream_openrouter` (pure Python)
- `stream_alchemy_openrouter` / `stream_alchemy_openai_completions` (Rust binding via PyO3)

This means you can target **any OpenAI-compatible** `/chat/completions` endpoint without maintaining a custom wrapper.

This has been live-verified with both Python and Rust paths, including Chutes
(`https://llm.chutes.ai/v1/chat/completions`) using `Qwen/Qwen3-32B`.

This unifies behavior in one provider path:

- consistent TinyAgent event streaming (`start`, `text_delta`, `tool_call_delta`, `done`)
- consistent message/tool conversion logic
- consistent usage contract shape and provider-raw semantics in final assistant messages

## When to Read

Read this guide when you need to:

- use TinyAgent with **non-OpenRouter OpenAI-compatible backends**
- point TinyAgent to **direct OpenAI** or **hosted compatible providers**
- run TinyAgent against **self-hosted/local** inference endpoints (vLLM, LM Studio proxy, etc.)
- use the Rust binding path with OpenRouterModel (`stream_alchemy_openrouter`)
- confirm compatibility for Chutes or other hosted OpenAI-compatible gateways
- delete provider-specific wrappers and standardize on TinyAgent’s native provider implementation

## What Changed

`OpenRouterModel` now includes:

```python
base_url: str = "https://openrouter.ai/api/v1/chat/completions"
```

Usage semantics are aligned across both provider paths:

- `usage.input` = provider-reported prompt/input tokens
- `usage.output` = provider-reported completion/output tokens
- `usage.total_tokens` = provider-reported total when present, else `input + output`
- cache fields map from provider cache-read/cache-write fields (including OpenAI-style nested details)
- reasoning-token breakdown fields are not folded into `usage.output`

And the providers now behave as follows:

### `stream_openrouter` (Python path)

1. resolves URL from `model.base_url` (fallback: OpenRouter default)
2. validates that `base_url` is a non-empty string
3. posts streaming requests to that resolved URL

### `stream_alchemy_openai_completions` / `stream_alchemy_openrouter` (Rust path)

1. accepts `OpenRouterModel` and `OpenAICompatModel`
2. resolves URL from `model.base_url` with the same non-empty validation behavior
3. supports endpoint-aware API key fallback
   - `OPENAI_API_KEY` when `provider == "openai"`
   - `OPENROUTER_API_KEY` when `provider == "openrouter"`

## Endpoint Contract

The target endpoint should be OpenAI-compatible for chat completions:

- accepts `POST` JSON payload with fields like `model`, `messages`, `stream`, optional `tools`
- returns SSE chunks similar to OpenAI/OpenRouter style deltas
- supports bearer auth in `Authorization: Bearer <token>` (or equivalent gateway behavior)

## Usage

### Default (OpenRouter)

```python
from tinyagent import OpenRouterModel

model = OpenRouterModel(
    id="anthropic/claude-3.5-sonnet",
)
```

### Direct OpenAI

```python
model = OpenRouterModel(
    id="gpt-4o-mini",
    base_url="https://api.openai.com/v1/chat/completions",
)
```

### Chutes example

```python
model = OpenRouterModel(
    id="Qwen/Qwen3-32B",
    base_url="https://llm.chutes.ai/v1/chat/completions",
)

response = await stream_openrouter(
    model,
    context,
    {
        "api_key": chutes_api_key,
        "temperature": 0,
        "max_tokens": 256,
    },
)
```

### Local/self-hosted endpoint

```python
model = OpenRouterModel(
    id="your-local-model-name",
    base_url="http://localhost:8000/v1/chat/completions",
)
```

### Rust binding path (PyO3)

Using `OpenRouterModel` (same model config object as Python path):

```python
from tinyagent import OpenRouterModel
from tinyagent.alchemy_provider import stream_alchemy_openrouter

model = OpenRouterModel(
    id="Qwen/Qwen3-32B",
    base_url="https://llm.chutes.ai/v1/chat/completions",
)

response = await stream_alchemy_openrouter(
    model,
    context,
    {"api_key": chutes_api_key, "temperature": 0, "max_tokens": 256},
)
```

Using `OpenAICompatModel` directly:

```python
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

model = OpenAICompatModel(
    provider="openrouter",  # or "openai" / custom label used in your integration
    id="Qwen/Qwen3-32B",
    base_url="https://llm.chutes.ai/v1/chat/completions",
)

response = await stream_alchemy_openai_completions(
    model,
    context,
    {"api_key": chutes_api_key},
)
```

## API Key Behavior

`stream_openrouter` resolves auth in this order:

1. `options["api_key"]`
2. `OPENROUTER_API_KEY` environment variable

`stream_alchemy_openai_completions` / `stream_alchemy_openrouter` resolve auth in this order:

1. `options["api_key"]`
2. `OPENAI_API_KEY` when `model.provider == "openai"`
3. `OPENROUTER_API_KEY` when `model.provider == "openrouter"`

For non-OpenRouter endpoints, passing `options["api_key"]` explicitly is recommended.
That keeps auth source unambiguous and avoids environment-variable mismatch.

## OpenRouter-Specific Routing Controls

`openrouter_provider` and `openrouter_route` are OpenRouter request-body controls.
They should generally be used only when `base_url` points to OpenRouter.

```python
model = OpenRouterModel(
    id="anthropic/claude-3.5-sonnet",
    openrouter_provider={"order": ["anthropic"]},
    openrouter_route="fallback",
)
```

## Validation and Test Coverage

### Automated tests

- `tests/test_openrouter_provider.py`
  - default URL fallback
  - base URL override
  - whitespace trimming
  - blank URL rejection

### Live smoke verification

Validated against:

- OpenRouter default endpoint (Python provider)
- OpenRouter endpoint via explicit `base_url` (Python provider)
- Chutes endpoint (`https://llm.chutes.ai/v1/chat/completions`) with `Qwen/Qwen3-32B` (Python provider)
- OpenRouter default endpoint via Rust binding (`stream_alchemy_openai_completions`)
- Chutes endpoint via Rust binding (`stream_alchemy_openrouter` + `OpenRouterModel`)

### Verified compatibility matrix

| Provider path | Endpoint | Model | Status |
|---|---|---|---|
| Python (`stream_openrouter`) | OpenRouter default | `openai/gpt-4o-mini` | ✅ |
| Python (`stream_openrouter`) | Chutes | `Qwen/Qwen3-32B` | ✅ |
| Rust (`stream_alchemy_openai_completions`) | OpenRouter default | `openai/gpt-4o-mini` | ✅ |
| Rust (`stream_alchemy_openrouter`) | Chutes | `Qwen/Qwen3-32B` | ✅ |

## Observed Backend Differences

Some reasoning-capable models (for example `Qwen/Qwen3-32B` on Chutes) may include
`<think> ... </think>` content before the final answer in text output.

This is model/backend behavior, not a TinyAgent provider parsing bug. TinyAgent streams
and returns what the backend emits.

If you need plain final answers only, enforce that in prompts or add a post-processing
step in your app layer.

## Troubleshooting

### `ValueError: Model \`base_url\` must be a non-empty string`

`base_url` is blank or only whitespace. Provide a full URL.

### 401 / 403 auth failures

- ensure correct key for the target backend
- pass `options["api_key"]` directly for endpoint-specific auth

### Model not found

Model IDs are backend-specific. Use IDs supported by the target endpoint.

## Related Docs

- [providers.md](providers.md)
- [README.md](../README.md)
- [caching.md](caching.md)
