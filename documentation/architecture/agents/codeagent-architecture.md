# TinyCodeAgent Architecture

This document maps how the Python-executing agent is wired, from prompt construction to sandboxed execution and finalization.

## Key Pieces
- **Entry point**: `tinyagent/agents/code.py` defines `TinyCodeAgent`, which orchestrates the ReAct-style loop.
- **LLM layer**: Uses `AsyncOpenAI` with the `CODE_SYSTEM` prompt (`tinyagent/prompts/templates.py`) loaded via `get_prompt_fallback`. The prompt lists tool names and optional suffix text.
- **Tool registry**: Functions decorated with `@tool` are resolved through `get_registry()`. The agent builds `_tool_map` and rejects async tools up front.
- **Execution backends**: `_init_executor()` picks an executor per `trust_level` (`LOCAL`, `ISOLATED`, `SANDBOXED`). All currently map to `LocalExecutor` (`tinyagent/execution/local.py`), with TODOs for isolated/sandboxed backends.
- **Signals and helpers**: The executor namespace is injected with registered tools plus `uncertain`, `explore`, and `commit` signals, and a `final_answer()` helper that marks completion.
- **Limits and memory**: `ExecutionLimits` caps timeout/output/steps; `AgentMemory` tracks failures and can be re-injected into the prompt for context; `Finalizer` records the chosen answer source.

## Execution Lifecycle
1. **Construct messages**: System prompt (with tool list) + user task.
2. **LLM turn**: `_chat()` calls the model with temperature 0; responses are stripped.
3. **Code extraction**: `_extract_code()` pulls the first fenced ```python block. Missing code triggers a retry prompt.
4. **Sandboxed run**: `_executor.run(code)` executes inside `LocalExecutor`, which:
   - Restricts builtins and import whitelist (`allowed_imports` + `extra_imports`).
   - Enforces timeout via `ExecutionLimits.timeout_context()`.
   - Captures stdout and watches for `_final_result` set by `final_answer()`.
5. **Result handling**:
   - On `ExecutionResult.error` → build an error message plus tool doc hints and ask the model to fix.
   - On timeout → notify the model.
   - On `is_final` → truncate if needed, store with `Finalizer`, and return.
   - Otherwise → feed observation back as the next user message.
6. **Step limit**: After `max_steps` without a final answer, raise `StepLimitReached` (or return a `RunResult` when `return_result=True`).

## Safety & Trust
- **Trust levels**: User-facing API exposes `trust_level` to choose between local/isolated/sandboxed execution. Only the local path is implemented; higher-trust paths are placeholders for future backends.
- **Import gate**: AST inspection blocks imports outside the whitelist before execution starts.
- **Output control**: `ExecutionLimits.truncate_output()` trims oversized stdout and annotates truncation.
- **Timeouts**: Uses signals on Unix (main thread) or a timer fallback; raises `ExecutionTimeout`.

## How `final_answer()` Works
- Injected by `LocalExecutor` into the sandbox namespace.
- Setting `_final_result` with `FinalResult(value, verified_by)` marks completion.
- When present after exec, `ExecutionResult.is_final` is set and `final_value` carries the answer (stdout is still returned for logs).

## Data Contracts
- **Tools**: Must be sync callables; async tools raise `ValueError` at construction.
- **Messages**: The loop always uses OpenAI-compatible roles; code responses must be fenced in Python blocks.
- **Observations**: Non-final runs echo stdout (or placeholder `(no output)`) back to the model for the next reasoning step.
- **Sync executor by design**: The `run()` method is async for LLM calls, but `_executor.run()` is intentionally sync. Python's `exec()` cannot be awaited; blocking is acceptable for fast tool calls.
