---
title: OpenRouter Cache Miss Proof
summary: Evidence that TinyAgent generates cache-control metadata in Python but does not currently forward that metadata or session_id through the alchemy binding path used by OpenRouter.
last_updated: "2026-04-04"
---

# OpenRouter Cache Miss Proof

## Claim

The `openrouter` run with `openai/gpt-4.1-mini` did not report cache usage because the current alchemy path drops explicit caching metadata before the provider call, and it does not forward `session_id`.

This note records proof from both runtime artifacts and current source.

## Runtime Evidence

### 1. Real OpenRouter probe returned zero cache telemetry

Artifact:

- `.artifacts/runtime/openrouter_gpt41mini_cache_probe_2026-04-04.json`

Observed result:

- turn 1: `cache_read = 0`, `cache_write = 0`
- turn 2: `cache_read = 0`, `cache_write = 0`
- provider/model: `openrouter` / `openai/gpt-4.1-mini`

### 2. Python-side context does include `cache_control`

Artifact:

- `.artifacts/runtime/openrouter_cache_debug_payload_2026-04-04.json`

Observed result from that artifact:

- `python_context_has_cache_control = true`
- both user content blocks contain:

```json
{
  "type": "text",
  "text": "Reply with exactly: turn one acknowledged.",
  "cache_control": {
    "type": "ephemeral"
  }
}
```

The same artifact also shows:

- `session_id_on_agent = "prompt-caching-probe"`
- `simple_stream_options_fields = ["api_key", "temperature", "max_tokens", "signal"]`
- `session_id_forwarded_by_stream_options = false`

## Source Evidence

### 3. Python adds `cache_control` to user messages

In `tinyagent/caching.py:22`, `_annotate_user_messages()` copies the final user `TextContent` block and sets:

```python
annotated_block.cache_control = EPHEMERAL_CACHE.model_copy(deep=True)
```

That metadata is preserved by `dump_model_dumpable(...)` because `TextContent` itself carries `cache_control` in `tinyagent/agent_types.py:101`.

### 4. The Rust binding input type for user content has no `cache_control` field

In `rust/src/lib.rs:169`, `PyUserContentInput::Text` accepts only:

```rust
Text {
    #[serde(default)]
    text: Option<String>,
}
```

There is no `cache_control` field on the binding-side user text input.

### 5. The Rust conversion forwards only `text`

In `rust/src/lib.rs:642`, `convert_user_content(...)` builds:

```rust
UserContentBlock::Text(alchemy_llm::types::TextContent {
    text: text.unwrap_or_default(),
    text_signature: None,
})
```

No cache metadata is forwarded there.

### 6. `session_id` exists on `Agent` but is not sent to providers

`Agent` stores `session_id` in `tinyagent/agent.py:294`.

But stream options are built in `tinyagent/agent_loop.py:195` with only:

- `api_key`
- `signal`
- `temperature`
- `max_tokens`

That matches the current `SimpleStreamOptions` definition in `tinyagent/agent_types.py:286`, which has no `session_id` field.

The provider call in `tinyagent/alchemy_provider.py:313` forwards only those same option fields into `options_dict`.

## Conclusion

The evidence supports this sequence:

1. TinyAgent Python does generate `cache_control` on user text blocks.
2. That metadata is visible in the serialized Python message payload before the binding call.
3. The alchemy Rust binding does not model or forward `cache_control` for user text content.
4. `session_id` is stored on the `Agent` but not passed through provider options.
5. The OpenRouter `gpt-4.1-mini` run therefore reached the provider without TinyAgent’s explicit cache breakpoint/session wiring, and the provider returned zero cache telemetry.

## Residual Uncertainty

This proof explains why TinyAgent-side cache signaling is not making it through this path.

It does not by itself prove that OpenRouter `openai/gpt-4.1-mini` would report cache hits after the binding is fixed, because provider-side cache behavior and telemetry can still vary by backend/model.
