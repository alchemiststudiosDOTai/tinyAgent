# ReactAgent Architecture

The veteran. JSON-based tool calling without code execution.

## Philosophy

ReactAgent doesn't write code. He picks tools. Think. Pick. Call. See. Repeat.

He's not clever. He's correct.

## Key Pieces

- **Entry point**: `tinyagent/agents/react.py` defines `ReactAgent`, the JSON-parsing ReAct loop.
- **LLM layer**: Uses `AsyncOpenAI` with the `SYSTEM` prompt. No native function calling - parses JSON from text output.
- **Tool registry**: Functions decorated with `@tool` are resolved through `get_registry()`. Builds `_tool_map` at init.
- **No executor**: Tools are trusted functions. No sandbox, no import whitelist, no exec().

## Execution Lifecycle

1. **Construct messages**: System prompt (with tool list) + user task.
2. **LLM turn**: `_chat()` calls the model. Temperature ramps on parse failures.
3. **JSON extraction**: `_try_parse_json()` parses the response. Malformed JSON triggers retry with `BAD_JSON` prompt.
4. **Dispatch**:
   - `{"answer": "..."}` - Final answer, return immediately.
   - `{"tool": "x", "arguments": {...}}` - Execute tool, add observation, loop.
   - `{"scratchpad": "..."}` - Log thinking, continue.
5. **Tool execution**: `_safe_tool()` validates args, calls function, catches errors.
6. **Observation**: Result (or error) added to messages as user message.
7. **Step limit**: After `max_steps`, one final attempt to get answer.

## Data Flow

```
task
  |
  v
+-------+   JSON text   +-------+
|  LLM  | ------------> | parse |
+-------+               +-------+
  ^                         |
  |    {"tool": "x", ...}   |
  |         or              v
  |    {"answer": "..."}  +-------+
  |                       | route |
  |                       +-------+
  |                         |
  |      +---------+        |
  +------| observe |<-------+
         +---------+     (tool call)
               |
               v
            +------+
            | tool |
            +------+
```

## What ReactAgent Has

- **JSON parsing**: LLM outputs structured JSON as text
- **Scratchpad**: Optional `{"scratchpad": "..."}` for thinking
- **Temperature ramping**: Increases temp on parse failures
- **Observation truncation**: `MAX_OBS_LEN` prevents prompt blowup
- **Final attempt**: Last chance for answer at step limit
- **Verbose logging**: Full execution trace when enabled

## What ReactAgent Doesn't Need

- **Sandbox/executor**: Tools are trusted functions
- **Import whitelist**: No code execution
- **Signals**: No `uncertain()`, `explore()`, `commit()`
- **AgentMemory object**: Message history is the memory
- **Trust levels**: Everything runs in-process

## ReactAgent vs CodeAgent

| Aspect | ReactAgent | CodeAgent |
|--------|------------|-----------|
| LLM output | JSON text | Python code |
| Tool invocation | Direct function call | exec() in sandbox |
| Trust model | Tools trusted | Code sandboxed |
| Async tools | Yes (via `tool.run()`) | No |
| Memory | Message history | AgentMemory object |
| Complexity | Lower | Higher |
| Use case | Tool orchestration | Code generation |

## Design Decisions

- **JSON parsing over native function calling**: Works with any model, not just function-calling ones. More portable.
- **Temperature ramping**: Self-healing on malformed outputs. Increases creativity when stuck.
- **Scratchpad in JSON**: Lets LLM think without dedicated memory object. Simple.
- **Message history as memory**: No separate state to manage. The conversation IS the context.
- **Trusted tools**: If you're worried about tool safety, use CodeAgent with sandboxing instead.

## The Piccolo Principle

ReactAgent is the veteran. He shows up, does the job, doesn't need credit.

- Not as flashy as CodeAgent
- Simpler, more reliable
- Knows when to use which tool
- Fails fast, doesn't repeat mistakes
- The workhorse for tool orchestration tasks
