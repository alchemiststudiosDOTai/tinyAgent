# Contract Analysis: rust/src/types.rs vs vendor/alchemy-llm

## Purpose

This document maps the contract boundaries between:
- `tinyagent/rust/src/types.rs` — Python-facing Rust types
- `vendor/alchemy-llm/` — Alchemy LLM crate (actual streaming implementation)

The goal is to identify all conversion contracts that must be maintained during the Rust rewrite.

---

## 1. Usage Contract

### Current State

**vendor/alchemy-llm/src/types/usage.rs**
```rust
pub struct Usage {
    pub input: u32,
    pub output: u32,
    pub cache_read: u32,
    pub cache_write: u32,
    pub total_tokens: u32,
    pub cost: Cost,
}

pub struct Cost {
    pub input: f64,
    pub output: f64,
    pub cache_read: f64,
    pub cache_write: f64,
    pub total: f64,
}
```

**rust/src/types.rs**
```rust
pub struct UsagePayload {
    pub input: u32,
    pub output: u32,
    pub cache_read: u32,
    pub cache_write: u32,
    pub total_tokens: u32,
    pub cost: CostPayload,
}

pub struct CostPayload {
    pub input: f64,
    pub output: f64,
    pub cache_read: f64,
    pub cache_write: f64,
    pub total: f64,
}
```

### Contract: ✓ MATCHES

Field names and types are identical. No conversion logic needed.

---

## 2. StopReason Contract

### Current State

**vendor/alchemy-llm/src/types/usage.rs**
```rust
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum StopReason {
    Stop,
    Length,
    ToolUse,
    Error,
    Aborted,
}
```

**rust/src/types.rs**
```rust
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum StopReason {
    Complete,
    Error,
    Aborted,
    ToolCalls,
    Stop,
    Length,
    ToolUse,
}
```

### Contract: ⚠️ MISMATCH

| Aspect | alchemy-llm | rust/src/types.rs |
|--------|-------------|------------------|
| Serialization | lowercase (`stop`, `error`) | snake_case (`complete`, `tool_calls`) |
| Variants | `stop`, `length`, `tool_use`, `error`, `aborted` | `complete`, `stop`, `length`, `tool_use`, `tool_calls`, `error`, `aborted` |

**Required conversions:**
- `rust/src/types.rs::StopReason::Complete` ↔ alchemy `StopReason::Stop`
- `rust/src/types.rs::StopReason::ToolCalls` ↔ alchemy `StopReason::ToolUse`

**Note:** The Python contract expects `tool_calls` (PLAN.md line 52), so the Rust side must normalize.

---

## 3. Context Contract

### Current State

**vendor/alchemy-llm/src/types/message.rs**
```rust
pub struct Context {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub system_prompt: Option<String>,
    pub messages: Vec<Message>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tools: Option<Vec<Tool>>,
}
```

**rust/src/types.rs**
```rust
pub struct Context {
    pub system_prompt: String,
    pub messages: Vec<Message>,
    pub tools: Option<Vec<AgentTool>>,
}
```

### Contract: ⚠️ MISMATCH

| Aspect | alchemy-llm | rust/src/types.rs |
|--------|-------------|------------------|
| system_prompt | `Option<String>` | `String` |

**Required conversion:**
- `rust/src/types.rs::Context` → alchemy `Context`: convert empty string to `None`
- alchemy `Context` → `rust/src/types.rs::Context`: convert `None` to empty string

---

## 4. AssistantMessage Contract

### Current State

**vendor/alchemy-llm/src/types/message.rs**
```rust
pub struct AssistantMessage {
    pub content: Vec<Content>,
    pub api: Api,
    pub provider: Provider,
    pub model: String,
    pub usage: Usage,
    pub stop_reason: StopReason,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error_message: Option<String>,
    pub timestamp: i64,
}
```

**rust/src/types.rs**
```rust
pub struct AssistantMessage {
    pub role: AssistantRole,
    pub content: Vec<Option<AssistantContent>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stop_reason: Option<StopReason>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub api: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provider: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub usage: Option<UsagePayload>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error_message: Option<String>,
}
```

### Contract: ⚠️ MISMATCH

| Aspect | alchemy-llm | rust/src/types.rs |
|--------|-------------|------------------|
| role | N/A (inferred) | `AssistantRole` (default: "assistant") |
| content | `Vec<Content>` | `Vec<Option<AssistantContent>>` |
| stop_reason | Required (`StopReason`) | Optional (`Option<StopReason>`) |
| usage | Required (`Usage`) | Optional (`Option<UsagePayload>`) |
| timestamp | Required (`i64`) | Optional (`Option<i64>`) |
| api/provider/model | Embedded structs | Optional strings |

---

## 5. Content Types Contract

### Current State

**vendor/alchemy-llm/src/types/content.rs**
```rust
// See vendor/alchemy-llm/src/types/content.rs for full definitions
pub enum Content { ... }
pub struct TextContent { ... }
pub struct ToolCall { ... }
```

**rust/src/types.rs**
```rust
pub struct TextContent {
    pub type_name: TextContentType, // "type" field
    pub text: Option<String>,
    pub text_signature: Option<String>,
    pub cache_control: Option<CacheControl>,
}

pub struct ToolCallContent {
    pub type_name: ToolCallContentType,
    pub id: Option<String>,
    pub name: Option<String>,
    pub arguments: JsonObject,
    pub partial_json: Option<String>,
}

pub enum AssistantContent {
    Text(TextContent),
    Thinking(ThinkingContent),
    ToolCall(ToolCallContent),
}
```

### Contract: ⚠️ PARTIAL MATCH

**Requires investigation:**
- Check `vendor/alchemy-llm/src/types/content.rs` for exact field names and type tags
- Verify `ThinkingContent` presence in alchemy-llm
- Verify `cache_control` support

---

## 6. Event Contract

### Current State

**vendor/alchemy-llm/src/types/event.rs**
```rust
pub enum AssistantMessageEvent {
    Start { partial: AssistantMessage },
    TextStart { content_index: usize, partial: AssistantMessage },
    TextDelta { content_index: usize, delta: String, partial: AssistantMessage },
    TextEnd { content_index: usize, content: String, partial: AssistantMessage },
    ThinkingStart { ... },
    ThinkingDelta { ... },
    ThinkingEnd { ... },
    ToolCallStart { ... },
    ToolCallDelta { ... },
    ToolCallEnd { content_index: usize, tool_call: ToolCall, partial: AssistantMessage },
    Done { reason: StopReasonSuccess, message: AssistantMessage },
    Error { reason: StopReasonError, error: AssistantMessage },
}
```

**rust/src/types.rs**
```rust
pub struct AssistantMessageEvent {
    #[serde(rename = "type", skip_serializing_if = "Option::is_none")]
    pub event_type: Option<AssistantMessageEventType>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub partial: Option<AssistantMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content_index: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub delta: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content: Option<AssistantEventContent>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_call: Option<ToolCallContent>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<AssistantMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<AssistantEventError>,
}
```

### Contract: ⚠️ MISMATCH

| Aspect | alchemy-llm | rust/src/types.rs |
|--------|-------------|------------------|
| Structure | Rust enum (not serialized directly) | Serialized struct with `type` tag |
| Serialization | Per-variant structs | Flat struct with optional fields |
| Error handling | `Error { reason, error }` | `error: Option<AssistantEventError>` |

**Required conversion:** Convert between Rust enum variants and serialized tagged format.

---

## 7. Stream Interface Contract

### Current State

**vendor/alchemy-llm/src/providers/openai_completions.rs**
```rust
pub fn stream_openai_completions(
    model: &Model<OpenAICompletions>,
    context: &Context,
    options: OpenAICompletionsOptions,
) -> AssistantMessageEventStream

pub struct OpenAICompletionsOptions {
    pub api_key: Option<String>,
    pub temperature: Option<f64>,
    pub max_tokens: Option<u32>,
    pub tool_choice: Option<ToolChoice>,
    pub reasoning_effort: Option<ReasoningEffort>,
    pub headers: Option<HashMap<String, String>>,
    pub zai: Option<crate::types::ZaiChatCompletionsOptions>,
}
```

**tinyagent/alchemy_provider.py**
```python
async def stream_alchemy_openai_completions(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> AlchemyStreamResponse
```

### Contract: ⚠️ MISMATCH

| Aspect | alchemy-llm | rust/src/types.rs + Python |
|--------|-------------|---------------------------|
| Model | Generic `Model<OpenAICompletions>` | `Model` (flat struct) |
| API key resolution | Passed in options | Resolved in Python provider |
| Headers | `HashMap<String, String>` | `dict[str, str]` on `OpenAICompatModel` |
| Reasoning | `reasoning_effort: Option<ReasoningEffort>` | `reasoning: ReasoningMode` on model |

---

## 8. Provider/API Resolution Contract

### Current State

**tinyagent/alchemy_provider.py**
```python
_PROVIDER_API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "minimax-cn": "MINIMAX_CN_API_KEY",
}

def _resolve_provider(model: Model) -> str: ...
def _resolve_base_url(model: Model) -> str: ...
def _resolve_api_key(model: Model, options: SimpleStreamOptions) -> str | None: ...
def _canonicalize_api(raw_api: str) -> str: ...
def _resolve_model_api(model: Model, provider: str) -> str: ...
```

**vendor/alchemy-llm/src/providers/**

```rust
// Provider detection by base_url pattern
// See detect_compat() in openai_completions.rs
```

### Contract: ⚠️ PARTIAL

These resolution functions exist only in Python. For a self-contained Rust binding, these must be replicated in Rust.

---

## Summary: Required Conversion Contracts

| # | Contract | Direction | Status |
|---|----------|-----------|--------|
| 1 | Usage/Cost shapes | Bidirectional | ✓ Match |
| 2 | StopReason serialization | Bidirectional | ⚠️ Normalize case/concept |
| 3 | Context.system_prompt | Bidirectional | ⚠️ Option ↔ String |
| 4 | AssistantMessage optionality | alchemy → rust | ⚠️ Required → Optional |
| 5 | Content types | Bidirectional | ⚠️ Investigate full shapes |
| 6 | Event serialization | alchemy → rust | ⚠️ Enum → Tagged struct |
| 7 | Stream interface params | Bidirectional | ⚠️ Resolve model mapping |
| 8 | Provider/API resolution | Python → Rust | ⚠️ No Rust implementation |

---

## PLAN.md Phase Mapping

This section maps each contract to the relevant phase in `PLAN.md`.

| # | Contract | PLAN.md Phase | Sub-phase | Notes |
|---|----------|---------------|-----------|-------|
| 1 | Usage/Cost shapes | Phase 1A | JSON helpers | Shapes are done; normalization is Phase 2 |
| 2 | StopReason serialization | Phase 1A | JSON helpers | Phase 2: stop-reason normalization |
| 3 | Context.system_prompt | Phase 1C + Phase 2 | Types + `AgentContext -> Context` conversion | Phase 2: `Option<String>` ↔ `String` |
| 4 | AssistantMessage optionality | Phase 1B + Phase 2 | Content + return behavior | Phase 2: required → optional handling |
| 5 | Content types | Phase 1B | Content and message shapes | Full shape investigation needed |
| 6 | Event serialization | Phase 1D + Phase 2 | Events + event parsing | Phase 2: `AssistantMessageEvent` behavior |
| 7 | Stream interface params | Phase 2 | Provider/API resolution | Model mapping not yet designed |
| 8 | Provider/API resolution | Phase 2 | Provider resolution | Python-only; needs Rust implementation |

### Phase 2 Contract Breakdown

From PLAN.md line 161-169:

| Contract Item | Source Contracts |
|--------------|------------------|
| `AgentMessage -> Message` and `AgentContext -> Context` conversion | #3, #4 |
| `AssistantMessageEvent` and final `AssistantMessage` return behavior | #4, #6 |
| `usage` payload requirements | #1 |
| provider resolution, API resolution, base URL resolution, and API-key lookup | #7, #8 |
| `tinyagent._alchemy` import/load behavior | `alchemy_provider.py` lines 111-137 |
| proxy event parsing, stop-reason normalization, and tool-call partial JSON accumulation | #2, #6 |
| tool execution result shapes and event contracts | #5 |

### Phase 1 Items Needing Phase 2 Resolution

The following items were marked complete in Phase 1, but the contract analysis reveals they need Phase 2 work:

1. **StopReason** (`rust/src/types.rs`): Snake_case serialization is correct for Python, but alchemy-llm uses lowercase. Phase 2 must add normalization at the conversion boundary.

2. **Context.system_prompt** (`rust/src/types.rs`): Uses `String`, but alchemy-llm uses `Option<String>`. Phase 2 must define the conversion semantics.

3. **AssistantMessage.usage** (`rust/src/types.rs`): Optional in Python-facing types, but required in alchemy-llm. Phase 2 must define how to handle missing usage from alchemy.

4. **AssistantMessageEvent** (`rust/src/types.rs`): Shape is done, but Phase 2 must define exact serialization format and event ordering contract.

---

## Next Steps

1. **Resolve StopReason contract** — Define conversion between `complete`/`tool_calls` and `stop`/`tool_use`
2. **Define Context conversion** — Handle `Option<String>` ↔ `String` for system_prompt
3. **Map AssistantMessage optionality** — Decide how to handle required fields from alchemy
4. **Define event serialization format** — Confirm exact JSON structure Python expects
5. **Plan provider resolution** — Determine if this moves to Rust or stays Python-side
