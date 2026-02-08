# Research -- Prompt Caching in TinyAgent v2.5

**Date:** 2026-02-07
**Owner:** claude
**Phase:** Research
**Branch:** v2.5
**Commit:** 89c6e91

## Goal

Determine what prompt caching mechanisms exist (if any) in the tinyagent-v2 codebase,
including Anthropic-style `cache_control`, provider-level caching, session-based caching,
or any other strategy to reduce redundant token costs across multi-turn agent loops.

## Findings

### Verdict: No prompt caching is implemented.

The codebase has **zero functional prompt caching**. No provider sends caching headers,
`cache_control` blocks, or session identifiers in API requests. The system prompt and
full message history are re-sent in their entirety on every single LLM call within the
agent loop.

However, there is **structural scaffolding** -- dead fields and passive data preservation --
that suggests prompt caching was planned or is expected to be added.

---

### Scaffolding That Exists (But Does Nothing)

#### 1. `session_id` -- Dead Property

- **Declared** in `AgentOptions` at [`agent.py:258`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/tinyagent/agent.py#L258)
- **Stored** on `Agent._session_id` at [`agent.py:294`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/tinyagent/agent.py#L294)
- **Property getter/setter** at [`agent.py:299-309`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/tinyagent/agent.py#L299-L309)
- **Documented** in [`docs/api/agent.md:235`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/docs/api/agent.md#L235) as "Session ID used for provider caching"
- **Used in examples**: `docs/README.md:25,221` passes `session_id="my-session"` to `AgentOptions`
- **Never passed downstream.** Not in `AgentLoopConfig`, `SimpleStreamOptions`, or any provider request body. Completely dead code.

#### 2. Content Signatures -- Passively Stored, Never Used

- `TextContent.text_signature` at [`agent_types.py:54`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/tinyagent/agent_types.py#L54)
- `ThinkingContent.thinking_signature` at [`agent_types.py:70`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/tinyagent/agent_types.py#L70)
- **Preserved by proxy** at [`proxy_event_handlers.py:161-172`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/tinyagent/proxy_event_handlers.py#L161-L172)
- **Preserved by Rust binding** at [`lib.rs:204-217`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/bindings/alchemy_llm_py/src/lib.rs#L204-L217)
- **Dropped during OpenRouter conversion** -- `_convert_assistant_message()` at [`openrouter_provider.py:85-117`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/tinyagent/openrouter_provider.py#L85-L117) only extracts `text` and `tool_call`, discarding signatures.
- These are Anthropic API artifacts for cached content blocks. They flow in from responses, get stored on messages, but are never sent back or acted upon.

#### 3. Cache Usage Counters -- Hardcoded Zeros

- `cacheRead` / `cacheWrite` in error-message usage dict at [`agent.py:215-221`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/tinyagent/agent.py#L215-L221)
- `cache_read` / `cache_write` in Rust `ModelCost` at [`lib.rs:541-545`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/bindings/alchemy_llm_py/src/lib.rs#L541-L545)
- All hardcoded to `0` / `0.0`. Never populated from actual provider responses.

---

### How Messages Flow Today (No Caching)

```
agent.prompt()
  -> _build_loop_context_and_config()     # agent.py:612-628
       reads self._state["system_prompt"]
       reads self._state["messages"]
       -> AgentContext(system_prompt, messages, tools)
  -> run_loop()                            # agent_loop.py:317-368
       -> stream_assistant_response()      # agent_loop.py:183-219
            -> _build_llm_context()        # agent_loop.py:99-116
                 optional transform_context()
                 convert_to_llm()
                 -> Context(system_prompt, messages, tools)  # FRESH EVERY TURN
            -> provider.stream(model, context, options)
```

On every turn of the inner agent loop, the **full system prompt + full message history**
is rebuilt and sent to the provider. There is no prefix marking, no breakpoint annotation,
no diff against prior turns.

### Provider-by-Provider Status

| Provider | File | Caching | Notes |
|----------|------|---------|-------|
| OpenRouter | `openrouter_provider.py` | None | Plain `{"role":"system","content":"..."}`. Two headers only: `Authorization` + `Content-Type`. No `anthropic-beta`. |
| Alchemy (Rust) | `alchemy_provider.py` + `lib.rs` | None | Passes plain `context_dict` to Rust. `options_dict` has only `api_key`, `temperature`, `max_tokens`. Has a `headers` field on `OpenAICompatModel` but unused for caching. |
| Proxy | `proxy.py` | Passthrough | Forwards whatever the proxy server returns. If the upstream server does its own caching, the proxy would transparently benefit, but tinyagent doesn't request or configure it. |

### Extension Point: `transform_context`

- Declared in `AgentLoopConfig.transform_context` at [`agent_types.py:362`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/tinyagent/agent_types.py#L362)
- Called in `_build_llm_context()` at [`agent_loop.py:107-108`](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/89c6e91/tinyagent/agent_loop.py#L107-L108)
- This is a user-supplied callback that could theoretically inject `cache_control` annotations before messages reach the provider. But the framework does not ship any built-in implementation.

---

## Key Patterns / Solutions Found

- **`session_id` is dead code**: Stored but never consumed. Would need to be threaded through `AgentLoopConfig` -> `SimpleStreamOptions` -> provider request to become functional.
- **Content signatures are preserved but dropped on re-send**: The proxy and Rust binding correctly parse and store them, but the OpenRouter provider discards them during format conversion. Even if caching were enabled, the signatures would be lost on round-trip through OpenRouter.
- **Usage stats schema exists but is unpopulated**: The data model supports `cacheRead`/`cacheWrite` but no provider actually populates these fields from API responses.
- **`transform_context` is the natural injection point**: If prompt caching were to be added, `transform_context` is where `cache_control` blocks could be injected onto message content before the provider call.

## Knowledge Gaps

1. **`alchemy-llm` Rust crate internals**: The upstream crate (`alchemy-llm` v0.1.1) is not vendored locally. It may have its own caching logic at the HTTP/SSE layer that we cannot verify from this repo alone.
2. **Proxy server behavior**: `proxy.py` forwards to an external proxy. That proxy server might implement server-side prompt caching (e.g., if it's an Anthropic-aware proxy), but tinyagent doesn't configure or request it.
3. **Original intent for `session_id`**: No documentation, comments, or commit messages explain what `session_id` was meant to enable. Was it for Anthropic prompt caching? For conversation continuity? For billing/tracking?

## References

- `tinyagent/agent.py` -- Agent class, session_id property, error message usage schema
- `tinyagent/agent_loop.py` -- Agent loop, `_build_llm_context()`, `stream_assistant_response()`
- `tinyagent/agent_types.py` -- `Context`, `SimpleStreamOptions`, `AgentLoopConfig`, content block types
- `tinyagent/openrouter_provider.py` -- OpenRouter HTTP provider, message conversion
- `tinyagent/alchemy_provider.py` -- Alchemy/Rust bridge provider
- `tinyagent/proxy.py` -- Proxy provider
- `tinyagent/proxy_event_handlers.py` -- Signature preservation from proxy events
- `bindings/alchemy_llm_py/src/lib.rs` -- Rust binding, ModelCost, signature serialization
- `docs/api/agent.md` -- session_id documentation
- `docs/README.md` -- session_id usage in examples
- `docs/ARCHITECTURE.md` -- Message handling architecture
