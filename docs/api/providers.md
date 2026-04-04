---
title: Providers
when_to_read:
  - When configuring provider integrations
  - When comparing the available stream provider paths
summary: Reference for TinyAgent provider implementations, configuration, and streaming behavior.
last_updated: "2026-04-04"
---

# Providers

LLM provider implementations that satisfy the `StreamFn` protocol.

## Alchemy Provider (Optional Binding)

TinyAgent keeps an OpenAI-compatible provider adapter in `alchemy_provider.py`.
The underlying `tinyagent._alchemy` extension is optional. During the migration
back into this repo, the historical external binding repo is:

- `https://github.com/alchemiststudiosDOTai/alchemy-rs`

Do not file binding/runtime issues against `tunahorse/tinyagent-alchemy`.

```python
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions
```

### OpenAICompatModel

```python
# In tinyagent.alchemy_provider
ReasoningEffort = Literal["minimal", "low", "medium", "high", "xhigh"]


class OpenAICompatModel(Model):
    provider: str = "openrouter"
    id: str = "moonshotai/kimi-k2.5"
    api: str = "openai-completions"

    base_url: str = "https://api.openai.com/v1/chat/completions"
    name: str | None = None
    headers: dict[str, str] | None = None
    context_window: int = 128_000
    max_tokens: int = 4096
    reasoning: bool | ReasoningEffort = False
```

Model configuration for OpenAI-compatible streaming through the optional binding.

`provider`, `api`, and `base_url` are resolved at call time:

- `provider` selects provider identity for env-key fallback and defaults
- `api` selects alchemy transport (`openai-completions` or `minimax-completions`)
- `base_url` sets the OpenAI-compatible endpoint URL

### stream_alchemy_openai_completions

```python
async def stream_alchemy_openai_completions(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> AlchemyStreamResponse
```

Stream using the optional `tinyagent._alchemy` implementation.

- `model.provider == "minimax"` or `"minimax-cn"` -> dispatches to minimax API
- all other providers dispatch to `openai-completions`
- explicit `model.api` wins; otherwise inferred from provider
- non-empty `model.base_url` is required
- returns an object implementing `StreamResponse`

### API key resolution order

For `stream_alchemy_openai_completions`:

1. `options.api_key`
2. `OPENAI_API_KEY` when `model.provider == "openai"`
3. `OPENROUTER_API_KEY` when `model.provider == "openrouter"`
4. `MINIMAX_API_KEY` when `model.provider == "minimax"`
5. `MINIMAX_CN_API_KEY` when `model.provider == "minimax-cn"`

If the binding is missing at runtime, `tinyagent.alchemy_provider` raises a
`RuntimeError`. For historical external binding issues during migration, use
`alchemy-rs`.

## Proxy Provider

Use the HTTP proxy provider when routing calls through a server-managed backend:

- `proxy.py`
- `proxy_event_handlers.py`

```python
from tinyagent import ProxyStreamOptions, stream_proxy, create_proxy_stream, parse_streaming_json
```

- `stream_proxy()` is protocol-compatible with `StreamFn`
- `create_proxy_stream()` is a convenience wrapper around `stream_proxy()`
- `parse_streaming_json()` is helpful for parsing streamed tool-argument fragments

## Usage Examples

### OpenAI-compatible endpoint (OpenAI)

```python
from tinyagent import Agent, AgentOptions
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

agent = Agent(
    AgentOptions(
        stream_fn=stream_alchemy_openai_completions,
    )
)
agent.set_model(
    OpenAICompatModel(
        provider="openai",
        id="gpt-4o-mini",
        api="openai-completions",  # optional (inferred when omitted)
        base_url="https://api.openai.com/v1/chat/completions",
    )
)
```

### OpenRouter-compatible endpoint

```python
agent.set_model(
    OpenAICompatModel(
        provider="openrouter",  # provider label used by your integration
        id="anthropic/claude-3.5-sonnet",
        base_url="https://openrouter.ai/api/v1/chat/completions",
        # OPENROUTER_API_KEY env fallback is supported; options.api_key still wins.
    )
)
```

### Chutes/OpenAI-compatible gateway

```python
agent.set_model(
    OpenAICompatModel(
        provider="openrouter",
        id="Qwen/Qwen3-Coder-Next-TEE",
        base_url="https://llm.chutes.ai/v1/chat/completions",
    )
)
```

### MiniMax endpoints

```python
agent.set_model(
    OpenAICompatModel(
        provider="minimax",
        id="MiniMax-M2.5",
        base_url="https://api.minimax.io/v1/chat/completions",
        # api optional; inferred as minimax-completions
    )
)

agent.set_model(
    OpenAICompatModel(
        provider="minimax-cn",
        id="MiniMax-M2.5",
        base_url="https://api.minimax.chat/v1/chat/completions",
        # api optional; inferred as minimax-completions
    )
)
```

### Reasoning mode

```python
model = OpenAICompatModel(
    provider="openrouter",
    id="deepseek/deepseek-r1",
    base_url="https://openrouter.ai/api/v1/chat/completions",
    reasoning="high",  # bool or "minimal" | "low" | "medium" | "high" | "xhigh"
)
```

## Streaming Events

Provider implementations emit `AssistantMessageEvent` values with these canonical event
names:

- `start`
- `text_start`, `text_delta`, `text_end`
- `thinking_start`, `thinking_delta`, `thinking_end`
- `tool_call_start`, `tool_call_delta`, `tool_call_end`
- `done`
- `error`

The agent loop translates these into `AgentEvent` lifecycle events.
