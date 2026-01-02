# Research - Agent Logging Output Map

**Date:** 2026-01-01
**Owner:** agent
**Phase:** Research

## Goal

Map all logging and output mechanisms in the tinyagent package to understand what produces console output during agent runs, enabling cleanup/removal of verbose logging.

## Findings

### Core Logging System

| File | Purpose |
|------|---------|
| `tinyagent/observability/logger.py` | AgentLogger class - centralized output with ASCII formatting |
| `tinyagent/observability/__init__.py` | Exports AgentLogger to public API |
| `tinyagent/agents/base.py:45` | Default logger instance (verbose=False) |

### Output Locations by Agent

#### TinyCodeAgent (`tinyagent/agents/code.py`)

**Logger calls (controlled by `verbose` flag):**
- Line 257: `logger.banner("TINYCODE AGENT v2 STARTING")`
- Line 258: `logger.labeled("TASK", task)`
- Line 264-272: `logger.labeled()` for trust level, limits, tools, imports
- Line 287: `logger.step_header(step_num, max_steps)`
- Line 290: `logger.messages_preview(messages)`
- Line 293: `logger.llm_response(reply)`
- Line 312: `logger.code_block(code)`
- Line 323-329: `logger.execution_result(...)`
- Line 348: `logger.error("No code block found in response")`
- Line 394: `logger.final_answer(output)`
- Line 448: `logger.api_call(self.model)`
- Line 455: `logger.api_response(len(content))`

**RAW PRINT STATEMENTS (ALWAYS OUTPUT - BYPASS LOGGER):**
- Lines 295-299: RAW LLM RESPONSE debug block
- Lines 306-310: EXTRACTED CODE debug block
- Lines 315-321: EXECUTION OUTPUT debug block

These 17 print statements are the primary offenders - they output regardless of verbose setting.

#### ReactAgent (`tinyagent/agents/react.py`)

**Logger calls (controlled by `verbose` flag):**
- Line 145: `logger.banner("REACT AGENT STARTING")`
- Line 146-148: `logger.labeled()` for task, system prompt, tools
- Line 165: `logger.step_header(step_num, max_steps)`
- Line 168: `logger.messages_preview(messages)`
- Line 171: `logger.llm_response(assistant_reply)`
- Line 198: `logger.error("JSON PARSE ERROR")`
- Line 203: `logger.scratchpad(payload["scratchpad"])`
- Line 221: `logger.final_answer(answer_value)`
- Line 251: `logger.error(f"Unknown tool '{name}'")`
- Line 262: `logger.tool_call(name, args)`
- Line 269: `logger.tool_observation(...)`
- Line 297: `logger.final_attempt_header()`
- Line 336: `logger.api_call(self.model, temperature)`
- Line 343: `logger.api_response(len(content))`
- Line 366: `logger.tool_error("ARGUMENT ERROR", str(exc))`
- Line 370: `logger.tool_executing(name, args)`
- Line 372: `logger.tool_result(str(result))`
- Line 375: `logger.tool_error("TOOL ERROR", str(exc))`

ReactAgent has NO raw print statements - all output goes through logger.

### AgentLogger Methods Available

| Method | Purpose |
|--------|---------|
| `banner(title)` | Full-width header with `+=====+` border |
| `labeled(tag, value)` | `[TAG] >> value` format |
| `step_header(n, max)` | `<< OPERATION n/max >>` panel |
| `messages_preview(msgs)` | Truncated message display |
| `llm_response(reply)` | LLM output display |
| `code_block(code)` | Numbered code lines |
| `execution_result(...)` | Code execution status |
| `final_answer(answer)` | Final result display |
| `api_call(model)` | API call indicator |
| `api_response(len)` | API response indicator |
| `tool_call(name, args)` | Tool invocation display |
| `tool_observation(...)` | Tool result display |
| `tool_error(type, msg)` | Error display |
| `error(msg)` | General error display |
| `scratchpad(text)` | Scratchpad content |
| `signal(type, msg)` | Signal display (uncertain/explore/commit) |

### Configuration

```python
@dataclass
class AgentLogger:
    verbose: bool = False              # Master toggle
    stream: TextIO = sys.stdout        # Output destination
    banner_width: int = 80             # Full banner width
    half_banner_width: int = 40        # Step header width
    content_preview_len: int = 200     # Content truncation
    observation_max_len: int = 500     # Observation truncation
    channel_label_width: int = 12      # Label padding
```

### Output Style

"Command Center" ASCII art formatting:
```
+==============================================================================+
| << COMMAND CENTER // TINYCODE AGENT v2 STARTING >>                          |
+==============================================================================+

[    TASK    ] >> What is 2 + 3?
[ TRUST LEVEL] >> local
```

No Rich library, no ANSI colors, plain text only.

## Key Patterns / Solutions Found

- **Two parallel output systems**: Structured logger (verbose-controlled) + raw print() (always on)
- **Verbose flag pattern**: All logger methods return early if `verbose=False`
- **Signal integration**: `set_signal_logger()` routes LLM signals through logger
- **Stream injection**: Can use `io.StringIO` for testing via `stream` parameter

## Knowledge Gaps

- Why were debug print statements added instead of using logger?
- Should signals output be tied to verbose or separate flag?

## Immediate Cleanup Targets

1. **Remove print statements** in `code.py:295-321` (17 statements)
2. Or convert them to logger calls with appropriate verbosity

## References

- `tinyagent/observability/logger.py` - AgentLogger implementation
- `tinyagent/agents/code.py` - TinyCodeAgent with debug prints
- `tinyagent/agents/react.py` - ReactAgent (clean, logger-only)
- `tinyagent/agents/base.py` - Base agent logger setup
- `tinyagent/signals/primitives.py` - Signal logger integration
