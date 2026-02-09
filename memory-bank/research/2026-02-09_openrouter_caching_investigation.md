# Research -- OpenRouter Prompt Caching Investigation
**Date:** 2026-02-09
**Phase:** Research

## Executive Summary

OpenRouter **officially supports** Anthropic prompt caching via `cache_control` blocks on its `/api/v1/chat/completions` endpoint. However, there are widespread reliability issues, reporting limitations, and a likely **minimum token threshold problem** in our test setup.

## Root Causes Identified (Ordered by Likelihood)

### 1. Minimum Token Threshold Not Met (HIGH confidence)

Anthropic's minimum cacheable prefix lengths:

| Model | Minimum Cacheable Tokens |
|-------|--------------------------|
| Claude Opus 4.5/4.6 | 4,096 |
| Claude Sonnet 4/4.5/3.7, Opus 4/4.1 | 1,024 |
| **Claude Haiku 3.5** | **2,048** |
| Claude Haiku 4.5 | 4,096 |

Our test uses `anthropic/claude-3.5-haiku` with a system prompt of ~1,223 tokens. **This is below the 2,048 minimum.** Caching silently does nothing when the prefix is too short -- no error, just `cached_tokens: 0`.

### 2. OpenRouter Does Not Report cache_write_tokens (CONFIRMED)

OpenRouter **does not return cache write tokens** in its SSE usage data, even when a cache write actually occurred. Only `cached_tokens` (reads) is populated on subsequent requests. Blog post by proredcat documents this and provides cost-derived calculation as a workaround.

This means:
- `cache_write_tokens: 0` is ALWAYS expected from OpenRouter, even when caching IS working
- `cached_tokens > 0` on the 2nd+ request would confirm caching works

### 3. `anthropic-beta` Header is Deprecated (SHOULD REMOVE)

The `anthropic-beta: prompt-caching-2024-07-31` header is deprecated. Prompt caching is GA. OpenRouter manages caching based on `cache_control` in the request body alone. Sending this header:
- Is unnecessary
- Could cause 400 errors when routed to certain providers (Vertex AI confirmed)
- Is not mentioned anywhere in OpenRouter's caching docs

### 4. OpenRouter Cache Stickiness is Best-Effort

Even with `"provider": {"order": ["Anthropic"]}`, OpenRouter load-balances across backend instances. Cache hits require hitting the same instance. OpenRouter says "best-effort" routing to the same provider, but it's not guaranteed.

## Codebase Analysis

### What We Send (Correct)
- System prompt: structured content array with `cache_control: {"type": "ephemeral"}` -- `openrouter_provider.py:468-481`
- User messages: structured content blocks with `cache_control` on last block of EVERY user message -- `caching.py:14-50`
- When caching detected, content is sent as array of objects (not flat string) -- `openrouter_provider.py:172-178`
- `anthropic-beta: prompt-caching-2024-07-31` header set -- `openrouter_provider.py:510-511` (SHOULD REMOVE)

### Usage Parsing (Correct)
- `_build_usage_dict()` reads both Anthropic-style top-level keys and OpenRouter `prompt_tokens_details` fallback -- `openrouter_provider.py:53-83`
- Handles `cache_write_tokens` in `prompt_tokens_details` (new) -- `openrouter_provider.py:64-66`

### EventStream Fix (Correct)
- Background task exceptions now propagate via `EventStream.set_exception()` -- `agent_types.py:449-459`
- `agent_loop()` registers `add_done_callback` to forward exceptions -- `agent_loop.py:388-394`
- Prevents silent hangs when provider errors

### Caching Transform (Correct)
- `_annotate_user_messages()` annotates ALL user messages (not just last) for cache stability across turns -- `caching.py:14-50`
- Immutable: uses `copy.copy()`, dict spread, list copies
- Composed via `_build_transform_context()` in `agent.py:249-264`

## Documentation Issue

`docs/api/caching.md:40` says "Last user message" but code annotates ALL user messages. Needs update.

## Actionable Next Steps

1. **Increase test system prompt to >=2,048 tokens** for Claude Haiku 3.5 (or switch to a Sonnet model with 1,024 minimum)
2. **Remove `anthropic-beta` header** -- deprecated, unnecessary, potentially harmful
3. **Stop expecting `cache_write_tokens`** from OpenRouter -- it always reports 0; only check `cached_tokens` on 2nd+ requests
4. **Update test_cache_live.py** to only assert `cached_tokens > 0` on turn 2 (not `cache_write_tokens`)
5. **Consider adding `cache_control` to tool definitions** (OpenRouter supports this since June 2025)
6. **Update docs/api/caching.md** to reflect "all user messages" behavior

## Community Evidence

| Project | Issue | Status | Finding |
|---------|-------|--------|---------|
| OpenRouter SDK #35 | Caching not working | Open | Only system prompt caching works |
| sst/opencode #1245 | Caching not scaling | Closed (fixed in PR #1305) | Fixed by adjusting breakpoints |
| Aider #1615 | Sonnet 3.5 caching | Open | Token costs same with/without |
| Goose #1066 | Caching not reducing costs | Open | Via OpenRouter |

## Sources

- https://openrouter.ai/docs/guides/best-practices/prompt-caching
- https://github.com/OpenRouterTeam/ai-sdk-provider/issues/35
- https://github.com/sst/opencode/issues/1245
- https://github.com/Aider-AI/aider/issues/1615
- https://github.com/block/goose/issues/1066
- https://github.com/anthropics/anthropic-cookbook/issues/175
- https://github.com/zed-industries/zed/issues/42715
- https://www.proredcat.xyz/blog/openrouter-cache-write-calculation
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching
