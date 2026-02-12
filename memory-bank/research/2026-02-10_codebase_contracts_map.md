# Research – tinyAgent Codebase Contracts Map
**Date:** 2026-02-10
**Phase:** Research

## Directory Structure

```
./
├── tinyagent/                    # Core Python package
│   ├── __init__.py               # Public API exports
│   ├── agent_types.py            # Foundation types (no internal deps)
│   ├── agent.py                  # Agent class, event handlers
│   ├── agent_loop.py             # Orchestration loop
│   ├── agent_tool_execution.py   # Tool execution logic
│   ├── caching.py                # Prompt caching transforms
│   ├── openrouter_provider.py    # OpenRouter API provider
│   ├── alchemy_provider.py       # Rust/PyO3 provider wrapper
│   ├── proxy.py                  # Proxy streaming infrastructure
│   ├── proxy_event_handlers.py   # SSE event handling
│   └── tools/builtin/            # Built-in tool implementations
├── src/lib.rs                    # Main Rust library (alchemy-llm)
├── bindings/alchemy_llm_py/      # PyO3 Python bindings
├── tests/                        # Test suite
│   ├── architecture/             # Import boundary tests
│   └── test_caching.py           # Caching tests
├── examples/                     # Usage examples
└── docs/                         # Documentation
```

## Core Contracts by Module

### 1. agent_types.py – Foundation Types

**Location:** `/root/tinyAgent/tinyagent/agent_types.py`

**Exported Types (TypedDict-based):**

| Type | Lines | Purpose |
|------|-------|---------|
| `UserMessage` | 95-100 | User input messages |
| `AssistantMessage` | 126-138 | Assistant response messages |
| `ToolResultMessage` | 140-150 | Tool execution results |
| `TextContent` | 54-57 | Text content blocks |
| `ImageContent` | 59-63 | Image content blocks |
| `ThinkingContent` | 65-69 | Thinking/reasoning content |
| `ToolCallContent` | 71-79 | Tool call content blocks |
| `AssistantContent` | 81-85 | Union of assistant content types |
| `Context` | 213-218 | LLM call context |
| `AgentContext` | 222-227 | Agent context with AgentMessage |
| `AgentState` | 406-418 | Agent runtime state |

**Dataclasses:**

| Class | Lines | Fields |
|-------|-------|--------|
| `Model` | 231-237 | provider, id, api, thinking_level |
| `OpenRouterModel` | 97-109 (in openrouter_provider.py) | +openrouter_provider, +openrouter_route |
| `OpenAICompatModel` | 64-81 (in alchemy_provider.py) | +base_url, +name, +headers, +context_window, +max_tokens, +reasoning |
| `Tool` | 191-196 | name, description, parameters |
| `AgentTool` | 198-205 | +label, +execute callback |
| `AgentToolResult` | 180-185 | content, details |

**Protocol Definitions:**

| Protocol | Lines | Methods |
|----------|-------|---------|
| `StreamResponse` | 294-302 | `result()`, `__aiter__()`, `__anext__()` |
| `AgentEvent` | 307-309 | Union type of all event types |
| `AssistantMessageEvent` | 265-275 | type, partial, delta, content_index |

**Type Aliases:**

```python
JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
StreamFn: TypeAlias = Callable[[Model, Context, SimpleStreamOptions], Awaitable["StreamResponse"]]
TransformContextFn: TypeAlias = Callable[[list[AgentMessage], asyncio.Event | None], Awaitable[list[AgentMessage]]]
ConvertToLLMFn: TypeAlias = Callable[[list[AgentMessage]], list[Message]]
```

**Constants:**

```python
STOP_REASONS: frozenset[str] = {"complete", "error", "aborted", "tool_calls", "stop", "length", "tool_use"}
STREAM_UPDATE_EVENTS: frozenset[str]  # Streaming event types
EPHEMERAL_CACHE: dict = {"type": "ephemeral"}  # in caching.py
```

**Event Classes (dataclass):**

| Class | Lines | Type Literal |
|-------|-------|--------------|
| `AgentStartEvent` | 310-312 | "agent_start" |
| `AgentEndEvent` | 315-318 | "agent_end" |
| `TurnStartEvent` | 321-323 | "turn_start" |
| `TurnEndEvent` | 326-330 | "turn_end" |
| `MessageStartEvent` | 333-336 | "message_start" |
| `MessageUpdateEvent` | 339-344 | "message_update" |
| `MessageEndEvent` | 347-349 | "message_end" |
| `ToolExecutionStartEvent` | 352-357 | "tool_execution_start" |
| `ToolExecutionUpdateEvent` | 360-367 | "tool_execution_update" |
| `ToolExecutionEndEvent` | 370-375 | "tool_execution_end" |

**EventStream Class:**

| Method | Lines | Purpose |
|--------|-------|---------|
| `__init__` | 428-438 | Initialize with is_end_event, get_result callbacks |
| `set_exception` | 447-451 | Terminate stream with exception |
| `__aiter__` | 453-454 | Async iterator protocol |
| `__anext__` | 456-467 | Get next event or raise StopAsyncIteration |

---

### 2. agent_loop.py – Orchestration Contract

**Location:** `/root/tinyAgent/tinyagent/agent_loop.py`

**Main Functions:**

| Function | Lines | Signature |
|----------|-------|-----------|
| `agent_loop` | 359-396 | `(config: AgentLoopConfig) -> EventStream` |
| `agent_loop_continue` | 398-445 | `(state: AgentLoopState) -> EventStream` |
| `run_loop` | 305-356 | `(config, signal, stream) -> None` |
| `_process_turn` | 233-302 | `(state, signal) -> TurnResult` |
| `stream_assistant_response` | 171-207 | `(state, signal) -> AssistantMessage` |
| `_build_llm_context` | 87-104 | `(state) -> Context` |

**AgentLoopConfig (TypedDict):**

```python
class AgentLoopConfig(TypedDict, total=False):
    model: Model
    system_prompt: str
    context: list[AgentMessage]
    tools: list[AgentTool] | None
    stream_fn: StreamFn
    transform_context: TransformContextFn | None
    convert_to_llm: ConvertToLLMFn | None
    max_iterations: int
    signal: asyncio.Event | None
    thinking_budgets: ThinkingBudgets | None
```

**Key Implementation Patterns:**
- Exception propagation via `task.add_done_callback(_done)` (lines 386-394)
- Steering message injection during tool execution
- Follow-up message queuing after turn completion

---

### 3. agent.py – Public API Contract

**Location:** `/root/tinyAgent/tinyagent/agent.py`

**AgentOptions (TypedDict):**

| Field | Type | Default |
|-------|------|---------|
| initial_state | AgentState | None |
| stream_fn | StreamFn | None |
| transform_context | TransformContextFn | None |
| convert_to_llm | ConvertToLLMFn | None |
| enable_prompt_caching | bool | False |
| session_id | str | None |
| get_api_key | ApiKeyResolverCallback | None |
| steering_mode | str | "one-at-a-time" |
| follow_up_mode | str | "one-at-a-time" |
| thinking_budgets | ThinkingBudgets | None |

**Agent Class:**

| Method | Lines | Purpose |
|--------|-------|---------|
| `__init__` | 288-320 | Initialize with opts, set up state and transforms |
| `prompt` | 452-533 | Synchronous prompt (collects all events) |
| `stream` | 452-533 | Async generator for streaming |
| `append_message` | 407-416 | Add message to state |
| `steer` | 418-444 | Inject steering messages mid-run |
| `on` | 398-405 | Register event listener |
| `abort` | 385-396 | Signal abort via asyncio.Event |

**Transform Composition (_build_transform_context):**

```python
def _build_transform_context(
    user_transform: TransformContextFn | None,
    enable_caching: bool,
) -> TransformContextFn | None
```

Caching runs first (if enabled), then user transform.

---

### 4. caching.py – Caching Transform Contract

**Location:** `/root/tinyAgent/tinyagent/caching.py`

**Functions:**

| Function | Lines | Signature |
|----------|-------|-----------|
| `_annotate_user_messages` | 14-50 | `(messages: list[AgentMessage]) -> list[AgentMessage]` |
| `add_cache_breakpoints` | 53-68 | `(messages, signal) -> list[AgentMessage]` |

**Contract:**
- Annotates ALL user messages' final content block with `cache_control: {"type": "ephemeral"}`
- Purpose: Prefix stability across conversation turns
- Returns new list (does not mutate input)

---

### 5. openrouter_provider.py – Provider Contract

**Location:** `/root/tinyAgent/tinyagent/openrouter_provider.py`

**Main Function:**

| Function | Lines | Signature |
|----------|-------|-----------|
| `stream_openrouter` | 562-616 | `(model, context, options) -> OpenRouterStreamResponse` |

**OpenRouterStreamResponse Class:**

| Method | Lines | Purpose |
|--------|-------|---------|
| `__init__` | 165-174 | Initialize with model, context, options |
| `__aiter__` | 176-177 | Async iterator |
| `__anext__` | 179-189 | Get next event |
| `result` | 191-198 | Get final AssistantMessage |
| `_run` | 200-228 | Main streaming loop |

**Key Helper Functions:**

| Function | Lines | Purpose |
|----------|-------|---------|
| `_context_has_cache_control` | 85-94 | Detect cache_control markers |
| `_convert_content_blocks_structured` | 152-165 | Convert to structured format preserving cache_control |
| `_add_openrouter_system_prompt` | 447-471 | Wrap system prompt with cache_control |
| `_build_usage_dict` | 46-82 | Normalize usage to standard format |
| `_parse_openrouter_sse_line` | 431-444 | Parse SSE lines |
| `_handle_text_delta` | 349-361 | Handle text delta events |
| `_handle_tool_call_delta` | 363-402 | Handle tool call delta events |

**Usage Dict Contract (_build_usage_dict):**

Returns standardized format:
```python
{
    "input": int,           # prompt_tokens
    "output": int,          # completion_tokens
    "cacheRead": int | None,
    "cacheWrite": int | None,
    "totalTokens": int,
    # Raw aliases for downstream compatibility:
    "prompt_tokens": int,
    "completion_tokens": int,
}
```

---

### 6. alchemy_provider.py – Rust Provider Contract

**Location:** `/root/tinyAgent/tinyagent/alchemy_provider.py`

**Main Function:**

| Function | Lines | Signature |
|----------|-------|-----------|
| `stream_alchemy_openai_completions` | 130-174 | `(model, context, options) -> AlchemyStreamResponse` |

**AlchemyStreamResponse Class:**

| Method | Lines | Purpose |
|--------|-------|---------|
| `result` | 91-101 | Get final message via `asyncio.to_thread()` |
| `__aiter__` | 103-104 | Async iterator |
| `__anext__` | 106-112 | Get next event via `asyncio.to_thread()` |

**OpenAICompatModel Dataclass:**

```python
@dataclass
class OpenAICompatModel(Model):
    provider: str = "openrouter"
    id: str = "moonshotai/kimi-k2.5"
    api: str = "openai-completions"
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    name: str | None = None
    headers: dict[str, str] | None = None
    context_window: int = 128_000
    max_tokens: int = 4096
    reasoning: bool = False
```

---

### 7. proxy.py – Proxy Provider Contract

**Location:** `/root/tinyAgent/tinyagent/proxy.py`

**Main Function:**

| Function | Lines | Signature |
|----------|-------|-----------|
| `stream_proxy` | 258-263 | `(model, context, options) -> ProxyStreamResponse` |
| `create_proxy_stream` | 265-321 | Higher-level proxy stream creation |

**ProxyStreamOptions Dataclass:**

```python
@dataclass
class ProxyStreamOptions:
    auth_token: str
    proxy_url: str
    temperature: float | None = None
    max_tokens: int | None = None
    reasoning: JsonValue | None = None
    signal: Callable[[], bool] | None = None
```

**ProxyStreamResponse Class:**

| Method | Lines | Purpose |
|--------|-------|---------|
| `__init__` | 165-174 | Initialize with model, context, options |
| `__aiter__` | 176-177 | Async iterator |
| `__anext__` | 179-183 | Get next event |
| `result` | 185-189 | Get final message |
| `_run` | 250-255 | Main run dispatcher |
| `_run_success` | 216-240 | Successful streaming path |
| `_run_error` | 242-247 | Error handling |

---

### 8. agent_tool_execution.py – Tool Execution Contract

**Location:** `/root/tinyAgent/tinyagent/agent_tool_execution.py`

**Main Function:**

| Function | Lines | Signature |
|----------|-------|-----------|
| `execute_tool_calls` | 130-179 | `(tools, assistant_message, signal, stream, get_steering_messages) -> ToolExecutionResult` |

**ToolExecutionResult (TypedDict):**

```python
class ToolExecutionResult(TypedDict):
    tool_results: list[ToolResultMessage]
    steering_messages: list[AgentMessage] | None
```

**Helper Functions:**

| Function | Lines | Purpose |
|----------|-------|---------|
| `validate_tool_arguments` | 25-50 | Validate tool call arguments against schema |
| `execute_single_tool` | 84-126 | Execute single tool with error handling |
| `get_tool_by_name` | 51-59 | Lookup tool by name |

---

### 9. proxy_event_handlers.py – Event Processing Contract

**Location:** `/root/tinyAgent/tinyagent/proxy_event_handlers.py`

**Main Function:**

| Function | Lines | Signature |
|----------|-------|-----------|
| `process_proxy_event` | 32-82 | `(proxy_event: JsonObject, partial: AssistantMessage) -> AssistantMessageEvent \| None` |

**Helper Functions:**

| Function | Lines | Purpose |
|----------|-------|---------|
| `_is_text_content` | 145-147 | Type guard for TextContent |
| `_is_tool_call` | 149-155 | Type guard for ToolCallContent |
| `_handle_text_delta` | 85-106 | Process text delta |
| `_handle_tool_call_delta` | 108-142 | Process tool call delta |
| `parse_streaming_json` | 158-192 | Parse partial/incremental JSON |

---

### 10. Rust Core (src/lib.rs)

**Location:** `/root/tinyAgent/src/lib.rs`

**PyO3 Module Structure:**

| Component | Lines | Purpose |
|-----------|-------|---------|
| `OpenAICompletionsStream` | 622-773 | PyClass exposing blocking methods |
| `message_to_alchemy` | 236-301 | Python message -> Rust alchemy-llm types |
| `assistant_message_to_py_value` | 303-350 | Rust message -> Python dict |
| `alchemize_event` | 352-470 | Convert alchemy events to Python JSON |
| `RUNTIME` | Static | Tokio runtime for async Rust |

**Key Methods on OpenAICompletionsStream:**

```rust
fn next_event(&self) -> Option<PyObject>  // Blocking, called via asyncio.to_thread
fn result(&self) -> PyObject               // Blocking, called via asyncio.to_thread
```

---

## Import Dependency Graph

```
agent_types.py (foundation - no internal deps)
    ↑
    ├── agent_loop.py (imports 14 items from agent_types)
    │       └── imports agent_tool_execution.py
    ├── agent.py (imports from agent_loop, agent_types, caching)
    ├── caching.py (imports from agent_types)
    ├── openrouter_provider.py (imports 11 items from agent_types)
    ├── alchemy_provider.py (imports 6 items from agent_types)
    ├── proxy.py (imports 8 items from agent_types)
    ├── proxy_event_handlers.py (imports 9 items from agent_types)
    └── agent_tool_execution.py (imports 12 items from agent_types)

__init__.py exports the public API from all modules
```

---

## Provider Pattern Contracts

All providers conform to `StreamFn` protocol:

```python
async def stream_provider(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> StreamResponse
```

**Response Objects Must Implement:**

| Method | Returns | Purpose |
|--------|---------|---------|
| `result()` | `Awaitable[AssistantMessage]` | Get final message |
| `__aiter__()` | `AsyncIterator[AssistantMessageEvent]` | Iterate events |
| `__anext__()` | `AssistantMessageEvent` | Get next event |

**Provider Implementations:**

| Provider | File | Transport | Notes |
|----------|------|-----------|-------|
| OpenRouter | openrouter_provider.py | httpx + SSE | Native Python, cache detection |
| Alchemy | alchemy_provider.py | PyO3 + Rust | asyncio.to_thread() bridge |
| Proxy | proxy.py | httpx streaming | Server-mediated calls |

---

## Event Stream Contract

**AssistantMessageEvent Structure:**

```python
{
    "type": "start" | "text_delta" | "tool_call_delta" | "done" | "error",
    "partial": AssistantMessage,  # Current accumulated message
    "delta": dict | None,         # Incremental change (for delta events)
    "content_index": int,         # Which content block is being updated
}
```

**Event Types:**

| Type | When Emitted | Delta Format |
|------|--------------|--------------|
| "start" | Stream begins | None |
| "text_delta" | Text chunk received | `{"text": str}` |
| "tool_call_delta" | Tool call chunk received | `{"id": str, "name": str, "arguments": str}` |
| "done" | Stream complete | None |
| "error" | Error occurred | None |

---

## Usage Tracking Contract

**Standardized Usage Dict (all providers):**

```python
{
    "input": int,              # Total input tokens
    "output": int,             # Total output tokens
    "cacheRead": int | None,   # Cache read tokens (if available)
    "cacheWrite": int | None,  # Cache write tokens (if available)
    "totalTokens": int,        # Total tokens
    # Raw aliases for compatibility:
    "prompt_tokens": int,
    "completion_tokens": int,
}
```

**OpenRouter Specific:**
- Reads cache info from `prompt_tokens_details.cached_tokens`
- OpenRouter never returns `cache_write_tokens` (reporting limitation)

---

## Error Handling Contracts

**EventStream Exception Propagation:**
- `set_exception(exc: BaseException)` terminates stream with error
- Prevents silent hangs on background task failures
- Used in agent_loop.py:386-394

**Agent-Level Error Handling:**
- Catches exceptions, converts to error messages
- Sets `AgentState.error` field
- Emits `AgentEndEvent` with error message

**Provider Error Patterns:**
- OpenRouter: Raises `RuntimeError` with status code and body
- Alchemy: Validates return types, raises `RuntimeError` on invalid
- Proxy: Sets stop_reason to "error" or "aborted", queues error event

**Tool Execution Error Handling:**
- Returns `(AgentToolResult, is_error: bool)` tuple
- Catches exceptions, returns error result with `is_error=True`

---

## State Management Contract

**AgentState (TypedDict):**

```python
{
    "system_prompt": str,
    "model": Model | None,
    "thinking_level": ThinkingLevel,
    "tools": list[AgentTool],
    "messages": list[AgentMessage],
    "is_streaming": bool,
    "stream_message": AgentMessage | None,
    "pending_tool_calls": set[str],
    "error": str | None,
}
```

**State Transitions:**
1. `prompt()`/`stream()` → sets `is_streaming=True`
2. Message events → updates `stream_message`
3. Tool execution → adds to `pending_tool_calls`
4. Completion/error → sets `is_streaming=False`, clears `stream_message`

---

## Type Guards/Validators

**Location:** Various files

| Function | File | Lines | Checks |
|----------|------|-------|--------|
| `_is_text_content` | openrouter_provider.py | 117-119 | block.get("type") == "text" |
| `_is_text_content` | proxy_event_handlers.py | 145-147 | block.get("type") == "text" |
| `_is_tool_call` | proxy_event_handlers.py | 149-155 | block.get("type") == "tool_call" |

---

## Public API Surface (__init__.py)

**Exported Classes:**
- `Agent`
- `AgentOptions`
- `Model`, `OpenRouterModel`
- `Tool`, `AgentTool`
- All event dataclasses
- All TypedDict message types

**Exported Functions:**
- `stream_openrouter`
- `stream_alchemy_openai_completions`
- `create_proxy_stream`
- `add_cache_breakpoints`

**Exported Types:**
- `Context`, `AgentContext`
- `AgentState`
- `StreamFn`, `TransformContextFn`, `ConvertToLLMFn`
- `ThinkingLevel`

---

## Test Boundaries

**Architecture Tests:**
- `/root/tinyAgent/tests/architecture/test_import_boundaries.py` – Enforces module import rules

**Caching Tests:**
- `/root/tinyAgent/tests/test_caching.py` – Caching functionality tests

---

## Summary of Key Contracts

1. **StreamFn Protocol:** All providers must implement `(Model, Context, SimpleStreamOptions) -> StreamResponse`

2. **TransformContextFn Protocol:** Context transforms must be `(list[AgentMessage], asyncio.Event | None) -> list[AgentMessage]`

3. **EventStream Protocol:** Must implement `result()`, `__aiter__()`, `__anext__()`, `set_exception()`

4. **Usage Dict Format:** Standardized to `{input, output, cacheRead, cacheWrite, totalTokens, prompt_tokens, completion_tokens}`

5. **Caching Transform:** Annotates ALL user messages with `cache_control: {"type": "ephemeral"}`

6. **Message Type Hierarchy:** `AgentMessage = Message | CustomAgentMessage`, `Message = UserMessage | AssistantMessage | ToolResultMessage`

7. **Content Block Types:** `TextContent`, `ImageContent`, `ThinkingContent`, `ToolCallContent`

8. **Error Propagation:** EventStream uses `set_exception()` to prevent silent hangs

9. **Import Direction:** `agent_types.py` is the foundation; all other modules import from it; no cycles

10. **Provider Detection:** OpenRouter detects `cache_control` in content blocks and switches to structured arrays
