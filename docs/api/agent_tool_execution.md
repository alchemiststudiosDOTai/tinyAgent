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
) -> ToolExecutionResult
```

Execute all tool calls found in an assistant message.

**Parameters**:
- `tools`: Available tools (looked up by name)
- `assistant_message`: The assistant message containing tool calls
- `signal`: Abort signal
- `stream`: Event stream to push execution events
- `get_steering_messages`: Callback to check for steering after all tools complete

**Returns**: `ToolExecutionResult` with tool results and optional steering messages

**Events Emitted**:
- `ToolExecutionStartEvent` (for all tools before execution begins)
- `ToolExecutionUpdateEvent` (if tool calls on_update during execution)
- `ToolExecutionEndEvent` (for all tools after execution, in original order)
- `MessageStartEvent`, `MessageEndEvent` (for each tool result, in order)

**Execution Flow** (parallel):
1. Extract tool calls from message content
2. Emit `ToolExecutionStartEvent` for all tools
3. Execute all tools concurrently via `asyncio.gather()`
4. Emit `ToolExecutionEndEvent` and `ToolResultMessage` events in original order
5. Check for steering messages once after all tools complete
6. Return results

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

**Current Implementation**: Returns arguments as-is (placeholder).

**Future**: Could use JSON Schema validation against `tool.parameters`.

## Internal Functions

### _extract_tool_calls
```python
def _extract_tool_calls(
    assistant_message: AssistantMessage
) -> list[ToolCallContent]
```

Extract all tool call content blocks from an assistant message.

Filters content list for items with `type == "tool_call"`.

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
) -> tuple[AgentToolResult, bool]
```

Execute a single tool and return (result, is_error).

**Error Handling**:
- Tool not found: Returns error result
- Tool has no execute function: Returns error result
- Exception during execution: Returns error result with exception message

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
class ToolExecutionResult(TypedDict):
    tool_results: list[ToolResultMessage]
    steering_messages: list[AgentMessage] | None
```

Result from executing tool calls.

- `tool_results`: Results for all executed tools
- `steering_messages`: If steering was queued during execution, the messages to process next

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
        content=[{"type": "text", "text": "Searching..."}]
    ))

    results = await perform_search(query)

    return AgentToolResult(
        content=[{"type": "text", "text": json.dumps(results)}],
        details={"result_count": len(results)}
    )
```
