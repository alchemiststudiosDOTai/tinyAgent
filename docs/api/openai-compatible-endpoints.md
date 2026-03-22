---
title: OpenAI-Compatible Endpoints via OpenAICompatModel
description: Use OpenAI-compatible `/chat/completions` endpoints with TinyAgent through `OpenAICompatModel`.
ontological_relations:
  - extends: providers.md
  - implemented_by: ../../tinyagent/alchemy_provider.py
  - validated_by: ../../tests/test_alchemy_provider.py
  - composes_with: agent.md#AgentOptions
---

# OpenAI-Compatible Endpoints via `OpenAICompatModel.base_url`

TinyAgent’s provider model supports a `base_url` override on `OpenAICompatModel`, so you can point to any OpenAI-compatible chat-completion endpoint without a custom wrapper.

- OpenRouter (via compatible endpoint URL)
- OpenAI directly
- Chutes or custom gateway endpoints
- Self-hosted/local compatible servers

## Summary

The optional alchemy binding path uses `stream_alchemy_openai_completions`.

```python
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions
```

`OpenAICompatModel` exposes:

- `provider`: backend identity used for dispatch and env-key fallback
- `api`: explicit alchemy API selector (`openai-completions`, `minimax-completions`)
- `base_url`: concrete endpoint used by the request

If `api` is omitted/blank, it is inferred:

- `provider in {"minimax", "minimax-cn"}` -> `minimax-completions`
- otherwise -> `openai-completions`

Legacy aliases are not required by the current provider path.

## Routing and auth

### API key resolution (provider)

1. `options.api_key`
2. `OPENAI_API_KEY` when `provider == "openai"`
3. `OPENROUTER_API_KEY` when `provider == "openrouter"`
4. `MINIMAX_API_KEY` when `provider == "minimax"`
5. `MINIMAX_CN_API_KEY` when `provider == "minimax-cn"`

For `provider="openrouter"`, env fallback works out of the box. Passing
`options.api_key` explicitly is still supported and takes precedence.

### Base URL behavior

- `base_url` must be a non-empty string.
- The value is forwarded directly into the binding-backed provider request.

### Usage semantics

- Message/tool conversion and usage contract are unified with the rest of TinyAgent.
- `usage` fields (`input`, `output`, `cache_read`, `cache_write`, `total_tokens`, `cost`) are normalized consistently by the provider layer.

## Endpoint contract requirements

The endpoint should be OpenAI-compatible for chat completions:

- accepts `POST` JSON payload with `model`, `messages`, `stream`, optional `tools`
- returns SSE or stream-like chunks that can map to assistant events
- bearer token auth via headers is supported by the endpoint

## Example usage

### OpenAI

```python
model = OpenAICompatModel(
    provider="openai",
    id="gpt-4o-mini",
    base_url="https://api.openai.com/v1/chat/completions",
)
```

### OpenRouter-compatible URL

```python
model = OpenAICompatModel(
    provider="openrouter",  # provider label used by your integration
    id="anthropic/claude-3.5-sonnet",
    base_url="https://openrouter.ai/api/v1/chat/completions",
)
```

### Chutes gateway

```python
model = OpenAICompatModel(
    provider="openrouter",
    id="Qwen/Qwen3-32B",
    base_url="https://llm.chutes.ai/v1/chat/completions",
)
```

### MiniMax

```python
model = OpenAICompatModel(
    provider="minimax",
    id="MiniMax-M2.5",
    base_url="https://api.minimax.io/v1/chat/completions",
)

model_cn = OpenAICompatModel(
    provider="minimax-cn",
    id="MiniMax-M2.5",
    base_url="https://api.minimax.chat/v1/chat/completions",
)
```

## Tool call streaming events

Providers emit the standard `AssistantMessageEvent` stream shape:

- `start`
- `text_start`, `text_delta`, `text_end`
- `thinking_start`, `thinking_delta`, `thinking_end`
- `tool_call_start`, `tool_call_delta`, `tool_call_end`
- `done`
- `error`

These are translated by `agent_loop` into `AgentEvent` stream events.

## Reasoning mode

For providers with reasoning support (for example DeepSeek R1), set
`reasoning` on `OpenAICompatModel`.

```python
model = OpenAICompatModel(
    provider="openrouter",
    id="deepseek/deepseek-r1",
    base_url="https://openrouter.ai/api/v1/chat/completions",
    reasoning="high",  # bool or "minimal" | "low" | "medium" | "high" | "xhigh"
)
```

When enabled, responses may include `ThinkingContent` blocks plus final answer text
blocks.

## Troubleshooting

- `RuntimeError: Model base_url must be a non-empty string`
  - `base_url` is blank/whitespace; provide a full URL.
- `401/403` authentication failures
  - pass `options.api_key` explicitly or use correct env var for the provider.
- model errors at runtime
  - verify model ID and endpoint compatibility with the target backend.
- alchemy binding import failures
  - install/build the optional binding from `https://github.com/tunahorse/tinyagent-alchemy`.
  - if the binding is already present, inspect the original import error now included in the
    raised `RuntimeError` to catch platform or loader mismatches.
