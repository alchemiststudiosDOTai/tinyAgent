---
title: Prompt Caching
description: Reduce token costs and latency by caching repeated prompt prefixes across turns.
ontological_relations:
  - composes_with: agent.md#AgentOptions
  - transforms: agent_types.md#AgentMessage
  - consumed_by: providers.md#OpenRouter-Provider
  - depends_on: agent_types.md#CacheControl
---

# Prompt Caching

Reduce token costs and latency by reusing cached prompt prefixes across conversation turns.

## When to Use

- Multi-turn conversations with a long system prompt (the system prompt is cached and reused every turn)
- Repeated interactions where the message history grows but the prefix stays stable
- Any workload where `input_tokens` dominates cost

**Requirements**:
- Anthropic models: cached prefix must meet the model’s minimum (e.g. Claude 3.5 Sonnet >= 1,024 tokens; Claude 3.5 Haiku >= 2,048 tokens)
- OpenAI models: caching is automatic when the provider supports `prompt_tokens_details`

**When NOT to use**:
- Single-shot prompts with no follow-up turns
- Very short system prompts (below the model’s cacheable-prefix minimum; caching will silently do nothing)

## How It Works

```
Turn 1:  [system_prompt + user_msg_1]  -->  cache MISS  (cache_write)
Turn 2:  [system_prompt + user_msg_1 + assistant_msg_1 + user_msg_2]  -->  cache HIT on prefix  (cache_read)
Turn 3:  [system_prompt + ... + user_msg_3]  -->  cache HIT on longer prefix  (cache_read)
```

Two things are annotated with `cache_control: {"type": "ephemeral"}`:

1. **System prompt** -- wrapped in a structured content block by the provider
2. **Every user message** -- each user message’s final content block gets the breakpoint (this keeps the cached prefix stable across turns)

The LLM provider caches everything up to the last breakpoint. On the next request, matching prefix tokens are read from cache instead of reprocessed.

## Usage

```python
from tinyagent import Agent, AgentOptions, OpenRouterModel, stream_openrouter

agent = Agent(
    AgentOptions(
        stream_fn=stream_openrouter,
        enable_prompt_caching=True,
    )
)
agent.set_model(OpenRouterModel(id="anthropic/claude-3.5-sonnet"))
agent.set_system_prompt("You are a helpful assistant. ...")

# Turn 1 -- populates the cache
msg1 = await agent.prompt("What is the capital of France?")
print(msg1["usage"])
# {"input": 3182, "output": 11, "cache_write": 0, "cache_read": 0, "total_tokens": 3193}

# Turn 2 -- reads from cache
msg2 = await agent.prompt("What is the capital of Germany?")
print(msg2["usage"])
# {"input": 3203, "output": 11, "cache_write": 0, "cache_read": 3178, "total_tokens": 3214}
```

## Composing with transform_context

When both `enable_prompt_caching` and a custom `transform_context` are set, caching runs first, then the custom transform receives the annotated messages.

```python
async def my_transform(messages, signal=None):
    # messages already have cache_control annotations here
    return messages

agent = Agent(
    AgentOptions(
        stream_fn=stream_openrouter,
        enable_prompt_caching=True,
        transform_context=my_transform,  # runs after caching
    )
)
```

## Direct Use

The transform function can be used standalone without the Agent class:

```python
from tinyagent.caching import add_cache_breakpoints

messages = [
    {"role": "user", "content": [{"type": "text", "text": "hello"}]},
]
annotated = await add_cache_breakpoints(messages)
# annotated[0]["content"][-1]["cache_control"] == {"type": "ephemeral"}
```

## add_cache_breakpoints

```python
async def add_cache_breakpoints(
    messages: list[AgentMessage],
    signal: asyncio.Event | None = None,
) -> list[AgentMessage]
```

Transform function matching the `TransformContextFn` signature.

Annotates every user message’s final content block with `cache_control: {"type": "ephemeral"}`. Does not mutate the original messages.

This is intentionally applied to *all* user messages (not just the last one) so that cache breakpoints remain stable across turns.

**Parameters**:
- `messages`: The conversation message list
- `signal`: Optional cancellation event (unused, present for signature compatibility)

**Returns**: A new message list with the cache breakpoint applied

## Usage Stats

The `usage` dict on assistant messages includes cache fields:

| Field | Description |
|-------|-------------|
| `input` | Provider-reported prompt/input tokens |
| `output` | Provider-reported completion/output tokens |
| `cache_read` | Tokens read from cache (saved reprocessing) |
| `cache_write` | Tokens written to cache (first-time cost) |
| `total_tokens` | Provider-reported total when available; otherwise `input + output` |

TinyAgent uses **provider-raw usage semantics** across Python and Rust providers:
- `output` is the provider-reported completion tokens
- reasoning-token breakdown fields (for example `completion_tokens_details.reasoning_tokens`) are **not** added into `output`

**Provider differences**:
- Anthropic-style payloads may report `cache_creation_input_tokens` and `cache_read_input_tokens`
- OpenAI-style payloads may report `prompt_tokens_details.cached_tokens` and `prompt_tokens_details.cache_write_tokens`
- OpenRouter may surface either variant depending on the upstream provider
- `cache_write` may be `0` when the provider does not report write stats (or reports them inconsistently)

## Provider Behavior

When caching is active, the OpenRouter provider:

1. Wraps the system prompt in a structured content block with `cache_control`
2. Emits structured content blocks (not flattened strings) for user messages that carry `cache_control`
3. Parses cache stats from the final SSE usage chunk (OpenRouter reporting can vary by upstream; rely primarily on `cache_read`, as `cache_write` may be 0/unreported)
