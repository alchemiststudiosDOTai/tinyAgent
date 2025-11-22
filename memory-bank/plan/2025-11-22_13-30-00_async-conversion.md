---
title: "TinyAgent Async Conversion – Implementation Plan"
phase: Plan
date: "2025-11-22 13:30:00"
owner: "Claude Planning Agent"
parent_research: "memory-bank/research/2025-11-22_13-10-10_async-conversion-mapping.md"
git_commit_at_plan: "3bd225f"
tags: [plan, async, conversion, architecture]
---

## Goal

**Convert TinyAgent framework from 100% synchronous to fully async architecture** to enable non-blocking I/O, concurrent tool execution, and modern Python async patterns. This is a complete async migration with NO sync patching or dual-mode support.

**Non-Goals**:
- Maintaining backwards compatibility with sync API
- Supporting sync tool wrappers
- Gradual migration (all-or-nothing approach)

## Scope & Assumptions

### In Scope
- OpenAI client migration (OpenAI → AsyncOpenAI) in 2 core agent files
- Tool registry async-aware execution with mixed sync/async tool support
- HTTP client migration (requests → httpx) for web tools
- Complete test infrastructure conversion to pytest-asyncio
- All 6 example files converted to async patterns
- Documentation updates for all code examples

### Out of Scope
- Sync API wrapper or backwards compatibility layer
- Database async drivers (no DB operations in codebase)
- File I/O async migration (sync file I/O is acceptable)
- Streaming response handling (not in current scope)

### Explicit Assumptions
1. **Breaking Change Accepted**: Users must migrate to async API, no sync fallback
2. **Python 3.10+**: asyncio.to_thread() available (added in 3.9)
3. **Single Event Loop**: One agent per event loop (no multi-agent concurrency initially)
4. **TinyCodeAgent Limitation**: exec() cannot support async/await - TinyCodeAgent explicitly rejects async tools with clear error. Use ReactAgent for async tools.
5. **Finalizer Threading**: Keep threading.Lock() (works with asyncio, asyncio.Lock() migration deferred)
6. **Pre-commit Hooks**: pytest remains commented out until migration complete, then re-enable

### Constraints
- All tests MUST pass before committing (golden baseline: pytest tests/api_test/test_agent.py -v)
- Incremental commits per phase with atomic changesets
- Follow existing code patterns exactly (type hints, error handling, docstrings)
- Run ruff check/format after every change

## Deliverables (DoD)

| Artifact | Acceptance Criteria |
|----------|---------------------|
| **Async Core** | ReactAgent.run() and TinyCodeAgent.run() are async, all OpenAI calls use AsyncOpenAI |
| **Tool Registry** | Tool.run() detects async tools, uses asyncio.to_thread() for sync tools, all tool invocations non-blocking |
| **Async Tools** | web_search() and web_browse() use httpx AsyncClient, no blocking requests.get() calls |
| **Test Suite** | All 50+ test methods converted to async def, pytest-asyncio configured, 100% test pass rate |
| **Examples** | All 6 demo files use async/await pattern with asyncio.run(main()) wrapper |
| **Documentation** | README and 7+ doc files updated with async code examples |

**Success Metric**: `pytest tests/ -v` passes with 100% async implementation, no sync blocking calls remaining

## Readiness (DoR)

- [x] Research document complete with full codebase mapping
- [x] Git branch clean (on master, commit 3bd225f)
- [x] Virtual environment active (.venv)
- [x] Baseline tests passing: pytest tests/api_test/test_agent.py -v
- [x] Dependencies installed: openai>=1.0 (has AsyncOpenAI)
- [x] Decision: TinyCodeAgent will reject async tools (best practice - separation of concerns)
- [x] Decision: threading.Lock() stays (defer asyncio.Lock() migration)
- [x] Decision: NO backwards compatibility needed (breaking v2.0 release)

## Milestones

### M1: Core Infrastructure (CRITICAL)
**Target**: Async-aware tool registry and execution engine
**Exit Criteria**: Tool.run() detects async functions, wraps sync tools with asyncio.to_thread(), basic validation tests pass

### M2: Agent Async Migration (CRITICAL)
**Target**: ReactAgent and TinyCodeAgent fully async
**Exit Criteria**: Both agents use AsyncOpenAI, all run() methods async, _chat() methods await completions, TinyCodeAgent validates and rejects async tools

### M3: Builtin Tools & Dependencies (HIGH)
**Target**: All HTTP tools use httpx, dependencies updated
**Exit Criteria**: web_search() and web_browse() async with httpx, pyproject.toml has httpx + pytest-asyncio

### M4: Test Infrastructure Hardening (HIGH)
**Target**: Complete test suite async conversion
**Exit Criteria**: All 50+ test methods async, pytest-asyncio configured, 100% pass rate

### M5: Examples & Documentation (MEDIUM)
**Target**: All examples and docs updated
**Exit Criteria**: 6 demo files use asyncio.run(), 15+ doc files have async code examples

## Work Breakdown (Tasks)

### Phase 1: Core Infrastructure (M1)
**Dependencies**: None
**Owner**: Execute Agent
**Estimate**: 1 file, ~50 LOC changes

#### Task 1.1: Tool Registry Async Detection
**File**: `tinyagent/core/registry.py`
**Summary**: Add async detection and async-aware execution to Tool class

**Changes**:
- Add imports: `import inspect, asyncio` (top of file)
- Add `is_async: bool = False` field to Tool dataclass (line 29-44)
- Modify `register()` to detect async: `is_async=inspect.iscoroutinefunction(fn)` (line 54-63)
- Convert `Tool.run()` to `async def run(self, payload: Dict[str, Any]) -> str`
- Implement async-aware execution:
  ```python
  if self.is_async:
      result = await self.fn(*bound.args, **bound.kwargs)
  else:
      result = await asyncio.to_thread(self.fn, *bound.args, **bound.kwargs)
  return str(result)
  ```
- Update `Tool.__call__()` to async or mark deprecated

**Acceptance Tests**:
- [ ] Sync tool (e.g., planning.create_plan) executes via asyncio.to_thread()
- [ ] Async tool (e.g., web_search) executes with await
- [ ] Tool.run() returns str for both sync/async tools
- [ ] Invalid tool call raises ValueError with clear message

**Files/Interfaces Touched**:
- tinyagent/core/registry.py:29-44 (Tool dataclass)
- tinyagent/core/registry.py:54-63 (register function)

---

### Phase 2: Agent Async Migration (M2)
**Dependencies**: Task 1.1 complete
**Owner**: Execute Agent
**Estimate**: 2 files, ~200 LOC changes

#### Task 2.1: ReactAgent Async Conversion
**File**: `tinyagent/agents/react.py`
**Summary**: Convert ReactAgent to fully async with AsyncOpenAI

**Changes**:
- Line 19: `from openai import OpenAI` → `from openai import AsyncOpenAI`
- Line 84: `self.client = OpenAI(...)` → `self.client = AsyncOpenAI(...)`
- Line 98: `def run(...)` → `async def run(...)`
- Line 152, 238: Add `await` before `self._chat()` calls
- Line 285: `def _chat(...)` → `async def _chat(...)`
- Line 291: Add `await` before `self.client.chat.completions.create(...)`
- Line 309: `def _safe_tool(...)` → `async def _safe_tool(...)`
- Line 332: Add `await` before `tool.run(args)`

**Acceptance Tests**:
- [ ] ReactAgent instantiates with AsyncOpenAI client
- [ ] agent.run() is awaitable and returns final answer
- [ ] Tool calls execute async (validated via mock)
- [ ] Error recovery still works with async flow

**Files/Interfaces Touched**:
- tinyagent/agents/react.py:19 (import)
- tinyagent/agents/react.py:84 (client init)
- tinyagent/agents/react.py:98-242 (run method)
- tinyagent/agents/react.py:285-300 (_chat method)
- tinyagent/agents/react.py:309-339 (_safe_tool method)

#### Task 2.2: TinyCodeAgent Async Conversion
**File**: `tinyagent/agents/code.py`
**Summary**: Convert TinyCodeAgent to async, add validation to reject async tools (exec() limitation)

**Changes**:
- Line 23: `from openai import OpenAI` → `from openai import AsyncOpenAI`
- Line 23: Add `import inspect` (for async tool validation)
- Line 216: `self.client = OpenAI(...)` → `self.client = AsyncOpenAI(...)`
- Line 233: `def run(...)` → `async def run(...)`
- Line 294: Add `await` before `self._chat()`
- Line 396: `def _chat(...)` → `async def _chat(...)`
- Line 400: Add `await` before `self.client.chat.completions.create(...)`
- **NEW**: Add validation in `__post_init__` (after existing tool validation):
  ```python
  # Validate no async tools (exec() doesn't support async/await)
  for name, tool in self.tools.items():
      if tool.is_async:
          raise ValueError(
              f"TinyCodeAgent does not support async tools: '{name}'. "
              f"Async tools (web_search, web_browse, etc.) require ReactAgent. "
              f"TinyCodeAgent is designed for synchronous code execution only."
          )
  ```

**Acceptance Tests**:
- [ ] TinyCodeAgent.run() is awaitable
- [ ] Generated code can call sync tools directly (planning tools work)
- [ ] Creating TinyCodeAgent with async tool raises ValueError with clear message
- [ ] PythonExecutor.run() stays sync (exec compatibility)

**Files/Interfaces Touched**:
- tinyagent/agents/code.py:23 (imports)
- tinyagent/agents/code.py:216 (client init)
- tinyagent/agents/code.py:__post_init__ (async tool validation)
- tinyagent/agents/code.py:233-294 (run method)
- tinyagent/agents/code.py:396-409 (_chat method)

---

### Phase 3: Builtin Tools & Dependencies (M3)
**Dependencies**: Task 2.1, 2.2 complete
**Owner**: Execute Agent
**Estimate**: 3 files, ~100 LOC changes

#### Task 3.1: Web Search Async Migration
**File**: `tinyagent/tools/builtin/web_search.py`
**Summary**: Replace requests with httpx for async HTTP

**Changes**:
- Line 10: `import requests` → `import httpx`
- Line 16: `def web_search(...)` → `async def web_search(...)`
- Line 30-42: Replace requests.get() with:
  ```python
  async with httpx.AsyncClient() as client:
      response = await client.get(url, headers=headers, params=params, timeout=10)
  ```

**Acceptance Tests**:
- [ ] web_search() is async and returns str
- [ ] HTTP call uses httpx AsyncClient
- [ ] Tool registry detects web_search as async (is_async=True)

**Files/Interfaces Touched**:
- tinyagent/tools/builtin/web_search.py:10 (import)
- tinyagent/tools/builtin/web_search.py:16 (function signature)
- tinyagent/tools/builtin/web_search.py:30-42 (HTTP call)

#### Task 3.2: Web Browse Async Migration
**File**: `tinyagent/tools/builtin/web_browse.py`
**Summary**: Replace requests with httpx for URL fetching

**Changes**:
- Line 8: `import requests` → `import httpx`
- Line 14: `def web_browse(...)` → `async def web_browse(...)`
- Line 42: Replace requests.get() with:
  ```python
  async with httpx.AsyncClient() as client:
      response = await client.get(url, headers=headers, timeout=10)
  ```

**Acceptance Tests**:
- [ ] web_browse() is async and returns str
- [ ] HTTP call uses httpx AsyncClient

**Files/Interfaces Touched**:
- tinyagent/tools/builtin/web_browse.py:8 (import)
- tinyagent/tools/builtin/web_browse.py:14 (function signature)
- tinyagent/tools/builtin/web_browse.py:42 (HTTP call)

#### Task 3.3: Dependency Updates
**File**: `pyproject.toml`
**Summary**: Add httpx and pytest-asyncio dependencies

**Changes**:
- Line 18-37: Add `httpx>=0.27.0` to dependencies
- Line 18-37: Add `pytest-asyncio>=0.23.0` to dependencies
- Line 89-94: Add to `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`
- Review: Keep `requests` or remove (check if used elsewhere)

**Acceptance Tests**:
- [ ] `uv sync` installs httpx and pytest-asyncio
- [ ] pytest detects async tests automatically (asyncio_mode = "auto")

**Files/Interfaces Touched**:
- pyproject.toml:18-37 (dependencies)
- pyproject.toml:89-94 (pytest config)

---

### Phase 4: Test Infrastructure (M4)
**Dependencies**: Phase 1-3 complete
**Owner**: Execute Agent
**Estimate**: 13 files, 50+ test methods

#### Task 4.1: Core API Tests (CRITICAL)
**Files**: tests/api_test/test_agent.py (330+ lines)
**Summary**: Convert all ReactAgent tests to async

**Pattern**:
```python
# Before
def test_agent_runs():
    agent = ReactAgent(tools=[get_weather], model="gpt-4o-mini")
    result = agent.run("What's the weather?")
    assert "sunny" in result.lower()

# After
@pytest.mark.asyncio
async def test_agent_runs():
    agent = ReactAgent(tools=[get_weather], model="gpt-4o-mini")
    result = await agent.run("What's the weather?")
    assert "sunny" in result.lower()
```

**Changes**:
- Convert all `def test_*` → `async def test_*`
- Add `await` before all `agent.run()` calls
- Add `@pytest.mark.asyncio` decorator (optional with auto mode)
- Update mocks to work with AsyncOpenAI (httpx-based)

**Files to Update**:
- tests/api_test/test_agent.py (50+ test methods)
- tests/api_test/test_agent_advanced.py
- tests/api_test/test_code_agent.py
- tests/api_test/test_web_browse.py (mock httpx instead of requests)

**Acceptance Tests**:
- [ ] ONE new contrastive test: test_async_tool_execution_vs_sync_tool_execution
  - Good: Async tool (web_search) executes with await, no blocking
  - Bad: Missing await raises TypeError
  - Side-by-side comparison showing async detection works

**Files/Interfaces Touched**:
- tests/api_test/*.py (all test methods)

#### Task 4.2: Unit Tests
**Files**: 9 unit test files
**Summary**: Update unit tests for async patterns

**Changes**:
- tests/test_agent_integration.py → async test methods
- tests/test_planning_tool.py → async test methods (tools stay sync, wrapped automatically)
- tests/prompt_test/test_code_agent.py → async test methods
- tests/prompt_test/test_react_agent.py → async test methods
- tests/test_exceptions.py → NO CHANGES (pure exception tests)
- tests/test_finalizer.py → NO CHANGES (threading.Lock() stays)
- tests/test_tool_validation.py → NO CHANGES (validation stays sync)
- tests/test_types.py → NO CHANGES (dataclass tests)
- tests/prompt_test/test_file_loader.py → NO CHANGES (sync file I/O)

**Acceptance Tests**:
- [ ] All unit tests pass with async agent methods

**Files/Interfaces Touched**:
- tests/test_*.py (specific test methods requiring async)

---

### Phase 5: Examples & Documentation (M5)
**Dependencies**: Phase 4 complete (tests passing)
**Owner**: Execute Agent
**Estimate**: 6 example files, 15+ doc files

#### Task 5.1: Example File Conversion
**Files**: examples/*.py (6 files)
**Summary**: Convert all demos to asyncio.run() pattern

**Pattern**:
```python
# Before
if __name__ == "__main__":
    agent = ReactAgent(tools=[get_weather], model="gpt-4o-mini")
    result = agent.run("What's the weather in Tokyo?")
    print(result)

# After
import asyncio

async def main():
    agent = ReactAgent(tools=[get_weather], model="gpt-4o-mini")
    result = await agent.run("What's the weather in Tokyo?")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

**Files to Update**:
- examples/simple_demo.py
- examples/react_demo.py
- examples/code_demo.py
- examples/file_prompt_demo.py
- examples/jina_reader_demo.py
- examples/rpg_demo.py

**Acceptance Tests**:
- [ ] All examples run without errors: `python examples/simple_demo.py`

**Files/Interfaces Touched**:
- examples/*.py (all demo files)

#### Task 5.2: Documentation Updates
**Files**: README.md + documentation/*.md (15+ files)
**Summary**: Update all code examples to async patterns

**Changes**:
- README.md - Main usage examples
- documentation/modules/agent.md - ReactAgent examples
- documentation/modules/code_agent.md - CodeAgent examples
- documentation/modules/tools.md - Tool creation examples
- documentation/examples/basic_usage.md
- documentation/examples/advanced.md
- documentation/examples/setup_andrun.md

**Pattern**: Add `import asyncio`, `async def main()`, `await agent.run()`, `asyncio.run(main())`

**Acceptance Tests**:
- [ ] All code examples in docs are async-correct (manual review)

**Files/Interfaces Touched**:
- README.md + documentation/modules/*.md + documentation/examples/*.md

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation | Trigger |
|------|--------|------------|------------|---------|
| **Async tool detection fails for edge cases** | HIGH | MEDIUM | Add comprehensive tests for sync/async/lambda/partial functions in test_tool_validation.py | Tool.run() raises TypeError at runtime |
| **AsyncOpenAI API changes from OpenAI SDK** | HIGH | LOW | Pin openai>=1.0,<2.0 in pyproject.toml, validate AsyncOpenAI.chat.completions API matches sync | Tests fail with AttributeError |
| **pytest-asyncio conflicts with existing test fixtures** | MEDIUM | LOW | Use asyncio_mode = "auto" to avoid manual decorators, isolate async tests | pytest collection errors |
| **TinyCodeAgent exec() limitation blocks async tools** | LOW | LOW | Explicit validation rejects async tools at agent creation with clear error message directing users to ReactAgent. Fail fast, not at runtime. | User tries to create TinyCodeAgent with async tool |
| **httpx timeout behavior differs from requests** | MEDIUM | MEDIUM | Match requests timeout defaults (10s), add explicit timeout tests | HTTP tools hang or timeout unexpectedly |
| **Backwards compatibility pressure from users** | LOW | MEDIUM | Clear CHANGELOG entry: "BREAKING: Full async migration, no sync wrapper provided. Pin tinyagent<2.0 for sync API" | GitHub issues requesting sync API |
| **Pre-commit pytest re-enable breaks CI** | MEDIUM | LOW | Re-enable pytest hooks AFTER all tests pass, add --tb=short for fast failure diagnosis | Pre-commit hook times out |

## Test Strategy

### Golden Baseline
**BEFORE any changes**:
```bash
source .venv/bin/activate
pytest tests/api_test/test_agent.py -v  # All tests must pass (baseline)
```

### Incremental Validation
**AFTER each phase**:
```bash
# Phase 1: Core Infrastructure
pytest tests/test_tool_validation.py -v  # Validate async tool detection

# Phase 2: Agent Migration
pytest tests/test_types.py -v  # Should still pass (no changes)

# Phase 3: Dependencies
uv sync  # Install httpx + pytest-asyncio

# Phase 4: Test Infrastructure
pytest tests/api_test/test_agent.py -v  # All async tests pass
pytest tests/ -v  # Full suite

# Phase 5: Examples
python examples/simple_demo.py  # Manual smoke test
```

### New Test (ONE Only)
**File**: tests/test_tool_validation.py
**Name**: test_async_tool_execution_vs_sync_tool_execution

**Good Example**:
```python
@tool
async def async_weather(city: str) -> str:
    await asyncio.sleep(0.01)  # Simulate async I/O
    return f"Async weather in {city}: sunny"

@pytest.mark.asyncio
async def test_async_tool_detected_and_executed():
    """Async tool should execute with await, no blocking"""
    tool = ToolRegistry.get("async_weather")
    assert tool.is_async is True
    result = await tool.run({"city": "Tokyo"})
    assert "sunny" in result
```

**Bad Example**:
```python
@pytest.mark.asyncio
async def test_sync_tool_missing_await_raises_error():
    """Forgetting await on async tool.run() should raise TypeError"""
    tool = ToolRegistry.get("async_weather")
    with pytest.raises(TypeError, match="object str can't be used in 'await'"):
        result = tool.run({"city": "Tokyo"})  # MISSING await
```

**Contrastive Value**: Side-by-side shows async detection works, and missing await fails fast with clear error.

### Final Gate
```bash
# All tests pass
pytest tests/ -v

# Linting clean
ruff check . --fix
ruff format .

# Pre-commit hooks (re-enabled)
pre-commit run --all-files

# Examples executable
for f in examples/*.py; do python "$f"; done
```

## References

### Research Document
- **Parent Research**: memory-bank/research/2025-11-22_13-10-10_async-conversion-mapping.md
- **Key Sections**:
  - Executive Summary (comprehensive async migration overview)
  - Section 1-2: Core agent files and tool registry (critical changes)
  - Section 3: Builtin tools (HTTP migration)
  - Section 5: Test infrastructure (50+ test methods)
  - Mechanical Changes Checklist (7-phase breakdown)

### GitHub Permalinks (Commit 3bd225f)
- ReactAgent: tinyagent/agents/react.py:98-242 (run method)
- TinyCodeAgent: tinyagent/agents/code.py:233-294 (run method)
- Tool Registry: tinyagent/core/registry.py:29-63 (Tool class + register)
- Web Search: tinyagent/tools/builtin/web_search.py:16-42 (HTTP blocking)
- Test Agent: tests/api_test/test_agent.py (golden baseline)

### External Dependencies
- **OpenAI SDK**: openai>=1.0 ([AsyncOpenAI docs](https://github.com/openai/openai-python))
- **httpx**: httpx>=0.27.0 ([Async client docs](https://www.python-httpx.org/async/))
- **pytest-asyncio**: pytest-asyncio>=0.23.0 ([Auto mode docs](https://pytest-asyncio.readthedocs.io/))

### Project Standards
- **CLAUDE.md**: Core workflow - test first, ruff always, match patterns
- **Contrastive Testing**: Create good vs bad examples for async tool detection
- **Pre-commit**: ruff + pytest hooks (re-enable after migration)

---

## Agents & Execution Strategy

### Subagent Deployment (Maximum 3)
1. **codebase-analyzer**: Validate tool registry async detection logic (Phase 1)
2. **context-synthesis**: Analyze completed phases for integration issues (Phase 4)
3. **lint-issue-resolver**: Fix ruff errors post-migration (Phase 5)

### Execution Order
1. Phase 1 (Core Infrastructure) → CRITICAL, blocks all other phases
2. Phase 2 (Agent Migration) → CRITICAL, depends on Phase 1
3. Phase 3 (Dependencies) → HIGH, parallel with Phase 2 completion
4. Phase 4 (Test Infrastructure) → HIGH, validates Phases 1-3
5. Phase 5 (Examples & Docs) → MEDIUM, final polish

### Atomic Commits
- Commit after each task completion with descriptive message
- Example: "feat: add async detection to Tool.run() with asyncio.to_thread wrapper"
- Run `ruff check . --fix && ruff format .` before each commit

---

## Final Gate

### Plan Summary
- **Plan Path**: memory-bank/plan/2025-11-22_13-30-00_async-conversion.md
- **Milestones**: 5 (M1: Infrastructure, M2: Agents, M3: Tools, M4: Tests, M5: Docs)
- **Tasks**: 10 (3 CRITICAL, 4 HIGH, 3 MEDIUM)
- **Gates**:
  - Golden baseline: pytest tests/api_test/test_agent.py -v MUST pass before start
  - Phase gates: Incremental test validation after each phase
  - Final gate: Full test suite + ruff + pre-commit + examples executable

### Next Command
```bash
/context-engineer:execute "memory-bank/plan/2025-11-22_13-30-00_async-conversion.md"
```

### Clarifications Resolved (Best Practices Applied)
1. **TinyCodeAgent Limitation**: ✅ RESOLVED - TinyCodeAgent will explicitly reject async tools with clear ValueError. This follows separation of concerns: ReactAgent handles async tools, TinyCodeAgent handles sync code execution.
2. **Finalizer Threading**: ✅ CONFIRMED - Keep threading.Lock() (works with asyncio, asyncio.Lock() migration deferred to future)
3. **Breaking Change**: ✅ CONFIRMED - NO backwards compatibility, full async migration (breaking change v2.0)

**READY FOR EXECUTION** - Plan follows best practices, no blockers remaining.
