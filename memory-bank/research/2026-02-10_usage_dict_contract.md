# Research -- Usage Dict Contract (`_build_usage_dict` raw vs. normalized keys)

**Date:** 2026-02-10
**Owner:** agent
**Phase:** Research

## Goal

Determine the current shape of `message["usage"]` across all provider paths, map the
normalization boundary, and evaluate Option A (raw aliases alongside normalized keys)
vs. Option B (pass raw dict through) for downstream compatibility with TunaCode and
other consumers.

## Findings

### Current Normalization Boundary

All raw-to-normalized mapping happens in exactly one function:

- [`_build_usage_dict()`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/488356a/tinyagent/openrouter_provider.py#L46-L79)

It reads six raw keys from the provider response and outputs five normalized keys:

| Raw Provider Key | Source | Normalized Key |
|---|---|---|
| `prompt_tokens` | OpenAI/OpenRouter | `input` |
| `completion_tokens` | OpenAI/OpenRouter | `output` |
| `cache_read_input_tokens` | Anthropic | `cacheRead` |
| `cache_creation_input_tokens` | Anthropic | `cacheWrite` |
| `prompt_tokens_details.cached_tokens` | OpenRouter/OpenAI | `cacheRead` (fallback) |
| `prompt_tokens_details.cache_write_tokens` | OpenRouter | `cacheWrite` (fallback) |

Output shape:

```json
{
  "input": 1234,
  "output": 567,
  "cacheRead": 100,
  "cacheWrite": 0,
  "totalTokens": 1801
}
```

Single call site: [`openrouter_provider.py:548`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/488356a/tinyagent/openrouter_provider.py#L548)

### Usage Shapes by Provider Path

| Provider | Where set | Normalization | Shape |
|---|---|---|---|
| **OpenRouter** | `openrouter_provider.py:548` via `_build_usage_dict()` | Yes | `{input, output, cacheRead, cacheWrite, totalTokens}` |
| **Proxy** | `proxy_event_handlers.py:278, :293` | **None** -- raw pass-through | Whatever the proxy server sends |
| **Alchemy (Rust)** | Rust binding `lib.rs:338` | **None** -- explicitly omitted | No `usage` key at all |
| **Error fallback** | `agent.py:216-223` | Hardcoded zeros | `{input, output, cacheRead, cacheWrite, totalTokens, cost}` |

The `AssistantMessage.usage` type is `JsonObject | None` ([`agent_types.py:136`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/488356a/tinyagent/agent_types.py#L136)) -- fully untyped, no schema enforcement.

### Data Flow: Provider -> Consumer

```
Provider response
    |
    v
_build_usage_dict() [OpenRouter only] or raw pass-through [Proxy]
    |
    v
partial["usage"] = dict
    |
    v
stream_assistant_response() -- agent_loop.py:205 -- returns AssistantMessage untouched
    |
    v
Consumers receive it via:
    1. Agent.prompt() return value         (agent.py:474-477)
    2. Agent.stream() MessageEndEvent      (agent_types.py:345-348)
    3. Agent.subscribe() callbacks          (agent.py:693-695)
    4. Agent.state["messages"] direct       (agent.py:381-382)
```

The agent loop performs **zero** transformation on usage between provider and consumer.
There is no dedicated `on_usage` callback -- usage is embedded in `AssistantMessage`.

### How TunaCode (and Other Consumers) Currently Break

TunaCode parses `message["usage"]` expecting raw OpenAI keys:
- `prompt_tokens`
- `completion_tokens`
- `prompt_tokens_details.cached_tokens`

Since v1.1.1, the OpenRouter provider normalizes these away. Consumers get `input` instead
of `prompt_tokens`, etc. The proxy path still passes raw keys through, so consumers using
a proxy backend are unaffected.

## Option Analysis

### Option A: Add Raw Aliases to `_build_usage_dict()`

Emit both normalized keys and raw OpenAI-compatible aliases:

```python
return {
    # normalized (tinyAgent canonical)
    "input": int(input_tokens),
    "output": int(output_tokens),
    "cacheRead": int(cache_read),
    "cacheWrite": int(cache_write),
    "totalTokens": int(input_tokens) + int(output_tokens),
    # raw aliases (OpenAI-compatible, for downstream consumers)
    "prompt_tokens": int(input_tokens),
    "completion_tokens": int(output_tokens),
}
```

**Pros:**
- Backward compatible -- existing consumers reading normalized keys are unaffected
- Downstream consumers expecting OpenAI keys get them without changes
- Single source of truth; no dual codepath
- Change is contained to one function (~2 lines added)

**Cons:**
- Dict grows; redundant data (same values under two key names)
- Sets precedent for tinyAgent to maintain OpenAI key compatibility indefinitely
- Does not include nested `prompt_tokens_details` -- consumers expecting that nested
  structure would still need changes

### Option B: Pass Raw Provider Dict Through Untouched

Remove `_build_usage_dict()` and stamp `parsed.usage` directly:

```python
partial["usage"] = parsed.usage  # raw dict from provider
```

**Pros:**
- Zero maintenance -- tinyAgent never normalizes, never breaks on new keys
- Consumers get exactly what the provider sends, including nested structures
- Proxy path already works this way, so this unifies behavior

**Cons:**
- Breaks existing tinyAgent internal consumers (`test_cache_live.py:37-40` reads
  `cacheRead`/`cacheWrite`)
- Error fallback in `agent.py:216-223` uses normalized keys -- would need updating
- Existing documentation and tests all reference normalized shape
- Different providers emit different raw shapes (Anthropic vs OpenAI vs OpenRouter),
  so consumers would need to handle multiple variants

## Recommendation

**Option A is the better fit.** Rationale:

1. **Minimal blast radius** -- 2 lines added to `_build_usage_dict()`, 1 test updated.
   No other code changes required.
2. **No breaking changes** -- all existing consumers (internal and external) continue working.
3. **The proxy path already demonstrates the pattern works** -- proxy consumers already
   handle raw keys; adding them to the OpenRouter path just unifies what's available.
4. **Option B would require migrating internal consumers** -- `test_cache_live.py`,
   error message construction, and all docs reference the normalized shape.

Consider also adding `prompt_tokens_details` as a nested pass-through for consumers
that need it (e.g., for `cached_tokens` introspection), but this can be deferred.

## Key Patterns / Solutions Found

- `_build_usage_dict()`: Single normalization boundary, well-isolated, easy to extend
- Proxy path: Already does raw pass-through (Option B pattern), proving it works for
  consumers that expect raw keys
- `JsonObject | None` typing: No schema enforcement means adding keys is non-breaking
  at the type level

## Knowledge Gaps

- Exact set of keys TunaCode reads from `message["usage"]` (only `prompt_tokens`,
  `completion_tokens`, and `prompt_tokens_details.cached_tokens` were mentioned)
- Whether TunaCode or other consumers also read Anthropic-native keys like
  `cache_read_input_tokens`
- Whether the `cost` sub-dict on error messages is consumed by anything downstream

## References

- [`tinyagent/openrouter_provider.py:46-79`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/488356a/tinyagent/openrouter_provider.py#L46-L79) -- `_build_usage_dict()`
- [`tinyagent/openrouter_provider.py:548`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/488356a/tinyagent/openrouter_provider.py#L548) -- call site
- [`tinyagent/proxy_event_handlers.py:273-295`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/488356a/tinyagent/proxy_event_handlers.py#L273-L295) -- proxy raw pass-through
- [`tinyagent/agent_types.py:136`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/488356a/tinyagent/agent_types.py#L136) -- `usage: JsonObject | None`
- [`tinyagent/agent.py:207-227`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/488356a/tinyagent/agent.py#L207-L227) -- error fallback usage
- [`tests/test_caching.py:157-189`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/488356a/tests/test_caching.py#L157-L189) -- `_build_usage_dict()` tests
- [`test_cache_live.py:29-40`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/488356a/test_cache_live.py#L29-L40) -- internal consumer reading normalized keys
