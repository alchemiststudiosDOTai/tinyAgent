# Architecture

This document describes the architecture of TinyAgent: where components live, what they do, and how they interact.

## Design Principles

1. **Streaming-first**: All LLM interactions support streaming; non-streaming is a special case
2. **Event-driven**: Components communicate through events for loose coupling
3. **Type safety**: Full type hints with Pydantic models for runtime messages/state and dataclasses for lifecycle events
4. **Boundary preservation**: AgentMessage (internal) vs Message (LLM-boundary) separation

## Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Agent                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   State     │  │  Listeners  │  │   Message Queues    │  │
│  │  (AgentState)│  │   (set)     │  │  (steering/follow-up)│ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agent Loop                             │
│         (agent_loop / agent_loop_continue)                  │
└─────────────────────────────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Stream    │     │   Execute   │     │   Transform     │
│   Function  │     │   Tools     │     │   Context       │
│(StreamFn)   │     │             │     │                 │
└─────────────┘     └─────────────┘     └─────────────────┘
```

## Module Responsibilities

### agent_types.py

**What**: Type definitions based on Pydantic runtime models (messages/state), dataclass lifecycle events, and shared type aliases.

**Key Types**:
- `AgentMessage`: Internal message format (union of Message + custom types)
- `Message`: LLM-compatible messages (user/assistant/tool_result)
- `AgentEvent`: All event types emitted during agent execution
- `AgentState`: Complete agent state snapshot
- `AgentTool`: Tool definition with execute function
- `StreamFn`: Protocol for LLM streaming implementations

**Design Decision**: Runtime model objects are normalized through typed models and event contracts at boundaries, avoiding parallel dict/model codepaths.

### agent_loop.py

**What**: Core agent execution loop. Single responsibility: orchestrate LLM calls and tool execution.

**Key Functions**:
- `agent_loop()`: Start new agent run with prompt messages
- `agent_loop_continue()`: Continue from existing context (for retries)
- `stream_assistant_response()`: Stream a single assistant message
- `run_loop()`: Main loop logic shared by both entry points

**Flow**:
1. Emit `AgentStartEvent`
2. Outer loop: Check for follow-up messages after agent would stop
3. Inner loop: Process turns (LLM call → tool execution → steering)
4. Emit `AgentEndEvent`

**Steering**: User can inject messages mid-run via `steer()`. During turns with tool calls, the loop polls steering after the parallel tool batch completes, then applies queued steering messages on the next turn.

### agent_tool_execution.py

**What**: Tool execution logic. Extracts tool calls from assistant messages and executes them.

**Key Functions**:
- `execute_tool_calls()`: Execute all tool calls in a message
- `skip_tool_call()`: Helper for synthetic skipped results in interruption-aware flows (not used in the default parallel path)
- `validate_tool_arguments()`: Validate args against tool schema (placeholder)

**Execution Flow**:
1. Extract tool calls from assistant message content
2. Emit `ToolExecutionStartEvent` for all calls
3. Execute all tool calls concurrently
4. Emit `ToolExecutionEndEvent` + result messages in original call order
5. Poll steering once after the batch completes
6. Return tool results as `ToolResultMessage` objects

### agent.py

**What**: High-level Agent class that wraps the agent loop with state management.

**Responsibilities**:
- Maintain `AgentState` (messages, tools, model, etc.)
- Manage event listeners
- Handle steering/follow-up message queues
- Provide sync-like interface (`prompt()`, `stream()`)
- Convert internal events to state updates

**Key Methods**:
- `prompt()`: Send message, wait for complete response
- `stream()`: Stream all agent events
- `stream_text()`: Stream just text deltas
- `steer()`: Queue a steering message that redirects the next turn
- `follow_up()`: Queue a message for after current run

**Event Handling**: Internal handlers update state on events:
- `message_start/update`: Update `stream_message` in state
- `message_end`: Append message to history
- `tool_execution_start/end`: Track pending tool calls
- `turn_end`: Capture errors from assistant messages
- `agent_end`: Mark streaming as complete

### Providers (`alchemy_provider.py`, `proxy.py`)

**What**: Implement `StreamFn` protocol for specific LLM backends.

**Rust Alchemy Provider**:
- PyO3-backed provider using `tinyagent._alchemy`
- OpenAI-compatible request/response model with OpenRouter-style endpoints
- Structured model/event pipeline and usage contract normalization
- Streaming via Rust-backed `Async` bridge

**Proxy Provider**:
- Uses `httpx` to call a relay service
- Parses proxy SSE into standard `AssistantMessageEvent` objects
- Keeps core event/message handling unchanged from the local provider flow

### Proxy provider details (`proxy.py`, `proxy_event_handlers.py`)

**What**: Client for apps that route LLM calls through a proxy server.

**Use Case**: Web apps where the server manages API keys and provider selection.

**Components**:
- `ProxyStreamResponse`: Implements `StreamResponse` for proxy SSE streams
- `process_proxy_event()`: Parse proxy-specific events into standard events

## Message Type Boundaries

```
┌─────────────────┐     convert_to_llm()     ┌─────────────────┐
│  AgentMessage   │ ───────────────────────► │     Message     │
│   (internal)    │                          │  (LLM boundary) │
│                 │ ◄─────────────────────── │                 │
│ - UserMessage   │     tool results         │ - user          │
│ - AssistantMsg  │                          │ - assistant     │
│ - ToolResult    │                          │ - tool_result   │
│ - Custom types  │                          │                 │
└─────────────────┘                          └─────────────────┘
```

The `convert_to_llm` callback filters custom message types before sending to LLM. This allows agents to maintain internal state (annotations, metadata) that isn't sent to the model.

Default implementation (`default_convert_to_llm`): Keep only `user`, `assistant`, and `tool_result` roles.

## Event System

Events flow upward through the system:

```
┌─────────────────────────────────────────────────────────┐
│  Provider (Alchemy/Proxy/custom StreamFn)               │
│  Emits: AssistantMessageEvent (text_delta, tool_call_*) │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Agent Loop                                             │
│  Translates: AssistantMessageEvent → AgentEvent         │
│  Emits: message_start, message_update, message_end      │
│         tool_execution_start, tool_execution_end        │
│         turn_start, turn_end, agent_start, agent_end    │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Agent Class                                            │
│  Updates state based on events                          │
│  Forwards events to subscribers                         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Application                                            │
│  Receives events, updates UI                            │
└─────────────────────────────────────────────────────────┘
```

## State Management

`AgentState` is a single source of truth represented as a Pydantic model:

```python
from tinyagent.agent_types import AgentState

state: AgentState
```

The model includes:

- `system_prompt`: active system prompt
- `model`: configured `Model` (or `None`)
- `thinking_level`: active reasoning level
- `tools`: configured tool definitions
- `messages`: conversation history (`AgentMessage` objects)
- `is_streaming`: whether a prompt loop is currently running
- `stream_message`: message currently streaming (if any)
- `pending_tool_calls`: active tool call IDs
- `error`: latest error text (if any)

State is mutated only by internal event handlers in the Agent class, keeping side effects centralized.

## Concurrency Model

- Agent runs in an asyncio task
- `agent_loop()` creates the task and returns immediately with an `EventStream`
- Application iterates the stream or awaits `result()`
- Steering uses thread-safe queues; agent checks queue at well-defined points
- Abort via `asyncio.Event` checked during streaming

## Extension Points

1. **Custom StreamFn**: Implement `StreamResponse` protocol for new providers
2. **convert_to_llm**: Filter/transform messages before LLM calls
3. **transform_context**: Modify context (e.g., add retrieval-augmented generation)
4. **get_api_key**: Dynamic API key resolution
5. **Custom AgentEvent**: Extend event types for domain-specific needs

## Code Quality Enforcement

This repository uses **blocking** pre-commit hooks (and should run the same checks in CI).
These checks are not advisory — they are enforced.

- `ruff` (lint + format)
- `mypy` (static typing)
- `archlint` + `layer-lock` (architecture boundary enforcement)
- `vulture` (dead code detection)
- `pylint` similarity checker (duplicate/clone detection)
- `debtlint` (technical debt tracking)

### Dead Code (vulture)

```bash
uv run vulture --min-confidence 80 tinyagent .vulture-whitelist.py
```

### Duplicate Code (pylint / R0801)

```bash
uv run pylint --disable=all --enable=duplicate-code tinyagent
```

## Technical Debt

No free-form TODO/FIXME/HACK/XXX/DEBT markers are allowed.
If you need to record technical debt, it must be tied to a real ticket in `.tickets/`.

Allowed formats (must be uppercase and include a ticket id):

```python
# TODO(tv-<ticket-id>): describe the debt and the intended fix
# FIXME(kap-<ticket-id>): describe the debt and the intended fix
# DEBT(tv-<ticket-id>): describe the debt and the intended fix
```

Enforcement:
- `scripts/lint_debt.py` is run via the `debtlint` pre-commit hook.
- It validates the format and ensures the referenced ticket exists and is not `closed`.
