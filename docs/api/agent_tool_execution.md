---
title: Agent Tool Execution Module
when_to_read:
  - When debugging tool-call execution
  - When checking how assistant tool calls are extracted and run
summary: Reference for TinyAgent's concurrent tool execution helpers and result handling.
last_updated: "2026-05-25"
---

# Agent Tool Execution Module

Tool execution logic for the agent loop. Extracts tool calls from assistant messages and executes them.

## Main Functions

### execute_tool_calls
```python
async def execute_tool_calls(
    tools: list[AgentTool] | None,
    assistant_message: AssistantMessage,
    signal: asyncio.Event | None,
    stream: EventStream,
    get_steering_messages: Callable[[], Awaitable[list[AgentMessage]]] | None = None,
    before_tool_call: BeforeToolCallFn | None = None,
    after_tool_call: AfterToolCallFn | None = None,
) -> ToolExecutionResult
```

Execute all tool calls found in an assistant message.

**Parameters**:
- `tools`: Available tools (looked up by name)
- `assistant_message`: The assistant message containing tool calls
- `signal`: Abort signal
- `stream`: Event stream to push execution events
- `get_steering_messages`: Optional callback polled once after the parallel tool batch completes
- `before_tool_call`: Optional host hook that can block a tool call with a structured result
- `after_tool_call`: Optional host hook that can inspect or override each result

**Returns**: `ToolExecutionResult` with tool results, optional steering messages, and a terminal batch flag

**Events Emitted**:
- `ToolExecutionStartEvent` (for all tools before execution begins)
- `ToolExecutionUpdateEvent` (if tool calls on_update during execution)
- `ToolExecutionEndEvent` (for all tools after execution, in original order)
- `MessageStartEvent`, `MessageEndEvent` (for each tool result, in order)

**Execution Flow** (parallel):
1. Extract tool calls from message content
2. Emit `ToolExecutionStartEvent` for all tools
3. Run `before_tool_call` for each tool, then execute unblocked tools concurrently via `asyncio.gather()`
4. Run `after_tool_call` before emitting each final result
5. Emit `ToolExecutionEndEvent` and `ToolResultMessage` events in original order
6. Check for steering messages once after all tools complete, unless the batch is terminal
7. Return results

**Steering semantics**: In parallel mode, all tool calls in the batch start before steering is polled. Steering redirects subsequent turns; it does not retroactively skip already-started tool calls.

**Loop-control semantics**: A tool can return `AgentToolResult(terminate=True)`,
or a hook can return `ToolLoopControl(terminate=True)`. The batch still emits
normal tool end and message events, then the agent loop ends without another
model turn.

**Event ordering**: All start events are emitted before any tool begins executing.
After all tools complete, end events and result messages are emitted in the
original tool call order. This ensures consumers see a clear parallel lifecycle:
all tools start → all tools finish → results delivered in order.

### skip_tool_call
```python
def skip_tool_call(
    tool_call: ToolCallContent,
    stream: EventStream
) -> ToolResultMessage
```

Skip a tool call due to user interruption (steering).

Creates a synthetic error result indicating the tool was skipped.

**Use Case**: Helper for interruption-aware execution paths that need synthetic skipped results. The current parallel `execute_tool_calls()` path does not call this helper.

### validate_tool_arguments
```python
def validate_tool_arguments(
    tool: AgentTool,
    tool_call: ToolCallContent
) -> JsonObject
```

Validate tool arguments against the tool's schema.

**Current Implementation**: Parses JSON-string arguments when needed, then returns a dict payload. No JSON Schema validation is performed in the current runtime.

## Internal Functions

### _extract_tool_calls
```python
def _extract_tool_calls(
    assistant_message: AssistantMessage
) -> list[ToolCallContent]
```

Extract all tool call content blocks from an assistant message.

### _find_tool
```python
def _find_tool(
    tools: list[AgentTool] | None,
    name: str
) -> AgentTool | None
```

Find a tool by name in the tools list.

Returns `None` if not found or tools is None.

### _execute_single_tool
```python
async def _execute_single_tool(
    tool: AgentTool | None,
    tool_call: ToolCallContent,
    signal: asyncio.Event | None,
    stream: EventStream,
    parent_task: asyncio.Task[object] | None,
    before_tool_call: BeforeToolCallFn | None,
) -> tuple[AgentToolResult, bool, bool]
```

Execute a single tool and return `(result, is_error, terminate)`.

**Error Handling**:
- Tool not found: Returns error result
- Tool has no execute function: Returns error result
- Tool raises `asyncio.CancelledError`: Returns an error result unless the current task itself is being cancelled (task cancellation propagates)
- Other exceptions during execution: Return an error result with exception message

**Progress Updates**:
If the tool calls `on_update(partial_result)`, emits `ToolExecutionUpdateEvent`.

### _create_tool_result_message
```python
def _create_tool_result_message(
    tool_call: ToolCallContent,
    result: AgentToolResult,
    is_error: bool,
) -> ToolResultMessage
```

Create a `ToolResultMessage` from execution result.

## Types

### ToolExecutionResult
```python
class ToolExecutionResult(BaseModel):
    tool_results: list[ToolResultMessage] = Field(default_factory=list)
    steering_messages: list[AgentMessage] | None = None
    terminate: bool = False
```

Result from executing tool calls.

- `tool_results`: Results for all executed tools
- `steering_messages`: Messages queued at the post-batch steering check (or `None` if none queued)
- `terminate`: Whether a tool result or hook marked the batch terminal

### ToolLoopControl

```python
@dataclass
class ToolLoopControl:
    terminate: bool = False
    result: AgentToolResult | None = None
    is_error: bool | None = None
```

`before_tool_call` may return a control object with `result` to skip execution
and emit that structured tool result. `after_tool_call` may return one to
replace the result, override `is_error`, or mark the batch terminal.

## Tool Execute Signature

Tools must implement this signature:

```python
async def execute(
    tool_call_id: str,      # Unique ID for this tool call
    args: JsonObject,       # Parsed arguments
    signal: asyncio.Event | None,  # Abort signal
    on_update: Callable[[AgentToolResult], None],  # Progress callback
) -> AgentToolResult:
    ...
```

**Example**:
```python
async def search_web(
    tool_call_id: str,
    args: dict,
    signal: asyncio.Event | None,
    on_update: Callable[[AgentToolResult], None],
) -> AgentToolResult:
    query = args.get("query", "")

    # Optional: send progress updates
    on_update(AgentToolResult(
        content=[TextContent(type="text", text="Searching...")]
    ))

    results = await perform_search(query)

    return AgentToolResult(
        content=[TextContent(type="text", text=json.dumps(results))],
        details={"result_count": len(results)}
    )
```

To end a repeated tool-call loop cleanly from inside a tool, return:

```python
return AgentToolResult(
    content=[TextContent(text="Stopping after repeated identical arguments.")],
    details={"policy": "same-tool-args"},
    terminate=True,
)
```
