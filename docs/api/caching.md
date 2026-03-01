---
title: Prompt Caching
description: Reduce token costs and latency by caching repeated prompt prefixes across turns.
ontological_relations:
  - composes_with: agent.md#AgentOptions
  - transforms: agent_types.md#AgentMessage
  - consumed_by: providers.md
  - depends_on: agent_types.md#CacheControl
---

# Prompt Caching

Reduce token costs and latency by reusing cached prompt prefixes across conversation turns.

## When to Use

- Multi-turn conversations with a stable long system prompt
- Repeated interactions where the prefix stays stable
- Workloads where prompt/input tokens dominate

**Requirements**:
- Provider must support cache-breakpoint semantics for your target backend
- Anthropic-style caching requires Claude-style minimum-prefix behavior
- OpenAI-style backends rely on prompt cache telemetry in usage details

## How It Works

```
Turn 1:  [system_prompt + user_msg_1]  --> cache MISS  (cache_write)
Turn 2:  [system_prompt + user_msg_1 + assistant_msg_1 + user_msg_2]  --> cache HIT  (cache_read)
Turn 3:  [system_prompt + ... + user_msg_3]  --> cache HIT on longer prefix (cache_read)
```

TinyAgent adds `cache_control: {"type": "ephemeral"}` in two places:

1. **System prompt** (provider-side wrapping behavior)
2. **Every user message** (final content block)

That keeps the cached prefix stable across turns, so repeated context can be reused.

## Usage

```python
from tinyagent import Agent, AgentOptions
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

agent = Agent(
    AgentOptions(
        stream_fn=stream_alchemy_openai_completions,
        enable_prompt_caching=True,
    )
)
agent.set_model(
    OpenAICompatModel(
        provider="openrouter",
        id="anthropic/claude-3.5-sonnet",
        base_url="https://openrouter.ai/api/v1/chat/completions",
    )
)
agent.set_system_prompt("You are a helpful assistant...")

# Turn 1 -- populates cache
msg1 = await agent.prompt("What is the capital of France?")
print(msg1.usage)

# Turn 2 -- should reuse prefix
msg2 = await agent.prompt("What is the capital of Germany?")
print(msg2.usage)
```

## Composing with `transform_context`

When both `enable_prompt_caching` and a custom `transform_context` are set, caching runs
first, then your transform sees already-annotated messages.

```python
async def my_transform(messages, signal=None):
    # messages already carry cache-control metadata
    return messages

agent = Agent(
    AgentOptions(
        stream_fn=stream_alchemy_openai_completions,
        enable_prompt_caching=True,
        transform_context=my_transform,  # runs after caching
    )
)
```

## Direct Use

The transform function can be used standalone without the Agent class:

```python
from tinyagent.caching import add_cache_breakpoints
from tinyagent import UserMessage, TextContent

messages = [
    UserMessage(content=[TextContent(text="hello")]),
]
annotated = await add_cache_breakpoints(messages)
print(annotated[0].content[-1].cache_control)
```

## add_cache_breakpoints

```python
async def add_cache_breakpoints(
    messages: list[AgentMessage],
    signal: asyncio.Event | None = None,
) -> list[AgentMessage]
```

Annotates every user message’s final content block with `cache_control` and returns the
updated message list.

## Usage Stats

The `usage` dict on assistant messages includes:

| Field | Description |
|-------|-------------|
| `input` | Provider-reported prompt/input tokens |
| `output` | Provider-reported completion/output tokens |
| `cache_read` | Tokens read from cache |
| `cache_write` | Tokens written to cache |
| `total_tokens` | Provider-reported total when available; otherwise `input + output` |

TinyAgent uses provider-raw usage semantics:
- `output` is provider-reported completion tokens
- reasoning token details are not folded into `output`

**Provider differences**:
- Anthropic-style payloads may use `cache_creation_input_tokens` and `cache_read_input_tokens`
- OpenAI-style payloads may use `prompt_tokens_details.cached_tokens` and `prompt_tokens_details.cache_write_tokens`
- `cache_write` may be `0` when a provider does not return it
