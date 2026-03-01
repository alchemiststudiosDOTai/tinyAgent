# Research – Type System Issues in tinyAgent
**Date:** 2026-03-01
**Phase:** Research

## Summary

Five type system design problems persist in tinyAgent after removing `openrouter_provider.py`. These are root architectural issues, not symptoms.

---

## Structure

```
tinyagent/
├── agent_types.py          Layer 0 (foundation) - Contains all type definitions
├── alchemy_provider.py     Layer 1 (leaf) - Provider implementation
├── caching.py              Layer 1 (leaf) - Cache control transforms
├── proxy.py                Layer 2 (coordination) - HTTP proxy provider
├── agent_loop.py           Layer 2 (coordination) - Event loop orchestration
├── agent.py                Layer 3 (orchestration) - Public API
├── agent_tool_execution.py Layer 1 (leaf) - Tool execution
└── proxy_event_handlers.py Layer 1 (leaf) - Proxy event translation
```

---

## Issue 1: Model Class Lacks Structure

### Location
- **Definition:** `agent_types.py:257-265`
- **getattr() cascades:** `alchemy_provider.py:202,209,250,290-294`

### Problem
`Model` is a plain `@dataclass` with 4 fields. `OpenAICompatModel` extends it with 6 additional optional fields. The alchemy provider uses `getattr()` with defaults to handle polymorphism:

```python
# alchemy_provider.py:285-295
model_dict: dict[str, Any] = {
    "id": model.id,
    "provider": provider,
    "api": api,
    "base_url": base_url,
    "name": getattr(model, "name", None),           # Subclass field
    "headers": getattr(model, "headers", None),     # Subclass field
    "reasoning": getattr(model, "reasoning", False), # Subclass field
    "context_window": getattr(model, "context_window", None),
    "max_tokens": getattr(model, "max_tokens", None),
}
```

### Impact
- 8× `getattr()` calls to access subclass fields
- No serialization protocol - manual dict construction
- Runtime probing instead of static type safety

---

## Issue 2: AgentEvent Union Lacks Discriminator Narrowing

### Location
- **Definition:** `agent_types.py:407-418`
- **getattr() usage:** `agent.py:67,100-102`

### Problem
`AgentEvent` is a Union of 10 dataclasses. Each has a `type: Literal["..."]` field, but no TypeGuard functions exist for narrowing. The code uses `getattr()` for optional attributes:

```python
# agent.py:67
tool_call_id = getattr(event, "tool_call_id", None)  # Only ToolExecution* events have this

# agent.py:100-102
msg = getattr(event, "message", None)
if getattr(msg, "role", None) == "assistant":
    error_message = getattr(msg, "error_message", None)
```

### Event Types
| Type Literal | Has `tool_call_id` | Has `message` |
|--------------|-------------------|---------------|
| `"agent_start"` | No | No |
| `"agent_end"` | No | No (has `messages`) |
| `"turn_start"` | No | No |
| `"turn_end"` | No | Yes |
| `"message_start"` | No | Yes |
| `"message_update"` | No | Yes |
| `"message_end"` | No | Yes |
| `"tool_execution_start"` | Yes | No |
| `"tool_execution_update"` | Yes | No |
| `"tool_execution_end"` | Yes | No |

### Impact
- Runtime probing with `getattr()` for union-specific attributes
- No compile-time guarantee of attribute existence
- Handler table dispatch works but individual handlers need unsafe access

---

## Issue 3: Union[PydanticModel, dict] for Messages

### Location
- **Primary:** `caching.py:85,94-97,101,110,123,156-158`
- **Secondary:** `alchemy_provider.py:70,79,98,170,191,196`
- **Secondary:** `proxy.py:83,89,132,159`
- **Secondary:** `agent_loop.py:119,127`

### Problem
caching.py handles both dict and Pydantic model messages throughout:

```python
# caching.py:94-97
content = (
    cast(list[object], msg.get("content", []))   # dict path
    if isinstance(msg, dict)
    else cast(list[object], msg.content)         # Pydantic path
)

# caching.py:110-113
if isinstance(block, TextContent):              # Pydantic path
    return block.text if isinstance(block.text, str) else None
if isinstance(block, dict) and block.get("type") == "text":  # dict path
    text_val = block.get("text")
```

### Functions Affected (caching.py)
| Function | Lines | isinstance Checks |
|----------|-------|-------------------|
| `_context_has_cache_control` | 62-82 | `isinstance(msg, dict)` |
| `_any_block_has_cache_control` | 85-102 | `isinstance(block, TextContent)`, `isinstance(block, dict)` |
| `_extract_text_from_block` | 105-113 | Both |
| `_convert_block_to_structured` | 116-129 | Both |
| `_convert_user_message` | 152-161 | `isinstance(msg, dict)` |

### Impact
- Every message access requires dual-path code
- 15+ `isinstance(msg, dict)` checks across codebase
- Double maintenance burden

---

## Issue 4: No Serializable Protocol

### Location
- **Probing code:** `alchemy_provider.py:193-198`, `proxy.py:86-91`

### Problem
Both providers duck-type Pydantic models to find `model_dump()`:

```python
# alchemy_provider.py:193-198
def _dump_model_payload(value: object, *, where: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return cast(dict[str, Any], value)
    model_dump = getattr(value, "model_dump", None)  # Probe for method
    if callable(model_dump):
        dumped = model_dump(exclude_none=True)
        if isinstance(dumped, dict):
            return cast(dict[str, Any], dumped)
    raise RuntimeError(f"{where}: unsupported payload type {type(value)!r}")
```

```python
# proxy.py:86-91 (identical pattern)
def _message_to_json(message: object) -> JsonObject:
    if isinstance(message, dict):
        return cast(JsonObject, message)
    model_dump = getattr(message, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(exclude_none=True)
        if isinstance(dumped, dict):
            return cast(JsonObject, dumped)
    raise TypeError(f"Unsupported message payload type...")
```

### Impact
- Duplicate serialization logic in 2+ files
- Runtime method probing instead of protocol/interface
- No static type checking of serializable objects
- Different error types (`RuntimeError` vs `TypeError`)

---

## Issue 5: cast(AgentEvent, ...) in EventStream

### Location
- **Definition:** `agent_types.py:450-537`
- **The cast:** `agent_types.py:518`

### Problem
`EventStream` uses a sentinel pattern with a queue typed as `asyncio.Queue[AgentEvent | object]`. The `object` is for `_WAKEUP_SENTINEL = object()`.

```python
# agent_types.py:465
self._queue: asyncio.Queue[AgentEvent | object] = asyncio.Queue()

# agent_types.py:509-518
queued_item = await self._queue.get()
if queued_item is self._WAKEUP_SENTINEL:
    # Handle sentinel...
    continue

event = cast(AgentEvent, queued_item)  # <-- The cast
```

### Why It's Needed
After checking `queued_item is self._WAKEUP_SENTINEL`, the type checker cannot narrow `object` to exclude the sentinel value. The cast bridges runtime check to static types.

### Impact
- Unsafe cast at core event streaming boundary
- Relies on runtime invariant (sentinel check) not encoded in types
- Type system cannot verify correctness

---

## Dependencies

### Type Flow Directions

```
Model:
  agent_types.py (definition)
    -> alchemy_provider.py (serialization via getattr)
    -> agent_loop.py (in AgentLoopConfig)
    -> agent.py (in AgentState)
    -> proxy.py (serialization to JSON)

AgentEvent:
  agent_types.py (definition)
    -> agent.py (dispatch via event.type + getattr for attrs)
    -> agent_loop.py (push to EventStream)
    -> agent_tool_execution.py (push tool events)

AgentMessage:
  agent_types.py (definition)
    -> caching.py (transform with dict/model duality)
    -> agent_loop.py (build context, convert to LLM format)
    -> alchemy_provider.py (serialize to dict for Rust)
    -> proxy.py (serialize to JSON)

Serialization:
  alchemy_provider.py --[model_dump probe]--> Rust binding
  proxy.py --[model_dump probe]--> HTTP JSON
```

---

## Symbol Index

### agent_types.py (Layer 0)
| Symbol | Type | Line |
|--------|------|------|
| `Model` | @dataclass | 257 |
| `AgentEvent` | Union alias | 407 |
| `EventStream` | class | 450 |
| `AgentMessage` | Union alias | 189 |
| `Message` | Union alias | 179 |
| `AssistantMessageEvent` | @dataclass | 280 |

### alchemy_provider.py (Layer 1)
| Symbol | Type | Line |
|--------|------|------|
| `OpenAICompatModel` | class(Model) | 124 |
| `_dump_model_payload` | function | 190 |
| `stream_alchemy_openai_completions` | StreamFn | 172 |

### caching.py (Layer 1)
| Symbol | Type | Line |
|--------|------|------|
| `add_cache_breakpoints` | TransformContextFn | 62 |

### agent.py (Layer 3)
| Symbol | Type | Line |
|--------|------|------|
| `_AGENT_EVENT_HANDLERS` | dict | 117 |
| `_handle_agent_event` | function | 141 |

---

## Patterns Found

1. **Structural Typing via getattr()** - Used for Model polymorphism and AgentEvent optional attributes
2. **Table-Driven Dispatch** - `_AGENT_EVENT_HANDLERS` maps event.type to handlers
3. **Dual-Path Branching** - `isinstance(x, dict)` checks throughout codebase
4. **Duck-Typed Serialization** - `getattr(obj, "model_dump", None)` probing
5. **Sentinel Pattern with Cast** - EventStream queue uses object() sentinel + cast

---

## Root Cause

The type boundaries are under-specified:
- `Model` should be a Pydantic base class with serialization
- `AgentEvent` should have TypeGuard narrowing functions
- Messages should be unified (all Pydantic or all dict at boundaries)
- `Serializable` protocol should be defined for `model_dump()`
- `EventStream` should use a typed discriminated union instead of cast
