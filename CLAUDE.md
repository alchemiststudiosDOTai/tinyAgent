# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is tinyAgent

tinyAgent (`tiny-agent-os` on PyPI) is a minimalist Python LLM agent framework with an optional Rust/PyO3 binding for native-speed streaming. v1.2.1, requires Python >=3.10. Beta -- APIs may change between minor versions.

Reference copy of alchemy-rs available at `/home/tuna/alchemy-rs-ref`.

## Build and Development

Hybrid Rust+Python build via maturin. Only runtime dependency is `httpx>=0.28.0`.

```bash
# Install for development (Rust binding + Python)
pip install maturin && maturin develop

# Optimized Rust build
maturin develop --release

# Install Python-only from PyPI (no Rust binding)
pip install tiny-agent-os
```

## Testing

```bash
pytest                                    # all tests
pytest tests/test_caching.py              # single file
pytest tests/test_caching.py::test_name   # single test
pytest -k "pattern"                       # by name pattern
pytest tests/architecture/ -x -q          # architecture enforcement only
```

`asyncio_mode = "auto"` is configured -- no need for `@pytest.mark.asyncio` on new tests.

## Linting and Quality

Pre-commit runs all checks. To run manually:

```bash
pre-commit run --all-files               # everything
ruff check . --fix                        # lint + autofix
ruff format .                             # format
uv run mypy --ignore-missing-imports --exclude 'lint_file_length\.py$' .
uv run vulture --min-confidence 80 tinyagent .vulture-whitelist.py
uv run pylint --disable=all --enable=duplicate-code tinyagent
python3 scripts/lint_architecture.py      # custom arch linter
python3 scripts/lint_binding_drift.py     # Rust binding drift check
python3 scripts/lint_debt.py              # tech debt tracker
```

Ruff config: line-length 100, max-complexity 10. Max file length: 500 lines (enforced by custom linter).

## Architecture

### Layered Module Hierarchy (enforced by grimp + pre-commit)

```
Layer 3 (orchestration):  agent
Layer 2 (coordination):   agent_loop, proxy
Layer 1 (leaf services):  agent_tool_execution, openrouter_provider,
                          alchemy_provider, proxy_event_handlers, caching
Layer 0 (foundation):     agent_types
```

Higher layers import lower. Siblings within a layer cannot import each other. `agent_types` imports nothing from tinyagent. Violations fail pre-commit via `tests/architecture/test_import_boundaries.py`.

### Key Abstractions

- **`StreamFn`** (`agent_types.py`): Provider abstraction -- a callable `(Model, Context, SimpleStreamOptions) -> Awaitable[StreamResponse]`. Three implementations: `stream_openrouter`, `stream_alchemy_openai_completions`, `stream_proxy`.
- **`StreamResponse`** (`agent_types.py`): Protocol (structural typing, not ABC) requiring `result()` and async iteration of `AssistantMessageEvent`.
- **`AgentTool`** (`agent_types.py`): Tool definition with `execute` callable signature `(tool_call_id, args, signal, on_update) -> AgentToolResult`.
- **`EventStream`** (`agent_types.py`): Internal async queue with exception propagation from background tasks.
- **Messages**: TypedDicts (`UserMessage`, `AssistantMessage`, `ToolResultMessage`), not dataclasses -- enables natural dict access and JSON serialization.

### Data Flow: `agent.prompt()` end-to-end

1. `Agent.prompt()` builds input messages, calls `_run_loop()`
2. `_run_loop()` creates `AgentContext` + `AgentLoopConfig`, calls `agent_loop()`
3. `agent_loop()` spawns a background `asyncio.Task` running `run_loop()`, returns `EventStream` immediately
4. `run_loop()` has a double-loop: outer checks follow-up messages, inner processes turns via `_process_turn()`
5. Each turn: emit pending messages -> call `stream_assistant_response()` -> execute tool calls -> check steering
6. `stream_assistant_response()` applies transform pipeline (caching + user transforms), calls `StreamFn`, dispatches events
7. Events flow back through `_AGENT_EVENT_HANDLERS` table in `agent.py` to update `AgentState` and notify subscribers

### Steering and Follow-up Queues

Two message queues interrupt or extend agent runs:
- **Steering**: Messages injected mid-run. Checked after each tool call -- remaining tool calls are skipped if steering arrives.
- **Follow-up**: Messages processed after the agent would normally stop.

### Rust Binding (`src/lib.rs` -> `tinyagent._alchemy`)

Global Tokio multi-thread runtime. Python calls `openai_completions_stream()` which deserializes via pythonize, calls `alchemy_llm::stream()`, sends events through `mpsc` channel. Python reads via blocking `next_event()` wrapped in `asyncio.to_thread`. Supports `openai-completions` and `minimax-completions` API dispatches.

### Provider-Specific API Key Env Vars

Alchemy provider resolves API keys from provider-specific env vars (e.g., `OPENROUTER_API_KEY`). See `alchemy_provider.py:_PROVIDER_API_KEY_ENV`.

## Design Patterns

- **Table-driven dispatch**: Event handlers in `agent.py` and `proxy_event_handlers.py` use dicts mapping event types to handler functions
- **Transform pipeline**: `convert_to_llm` + `transform_context` are composed in `agent.py` and applied in `agent_loop.py`
- **Background task + exception propagation**: `agent_loop()` runs in `asyncio.create_task()` with a done callback that forwards exceptions to the stream

## Conventions

- All modules use `from __future__ import annotations`
- Private functions prefixed with `_`, constants in `UPPER_CASE`, type aliases in `PascalCase`
- Public API is explicitly exported via `__init__.py` `__all__` -- all imports must go through the public surface
