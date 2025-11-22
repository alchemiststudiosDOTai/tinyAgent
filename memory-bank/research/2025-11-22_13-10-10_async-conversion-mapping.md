# Research – TinyAgent Async Conversion Codebase Mapping

**Date:** 2025-11-22
**Owner:** Claude Research Agent
**Phase:** Research
**Git Commit:** 3bd225f6297b49fcebd5f1904ecae33d9232a95d
**Branch:** master

## Goal

Map the complete codebase state before converting from synchronous to fully async architecture. This research provides a comprehensive inventory of all sync patterns, blocking operations, and mechanical changes needed for async conversion. NO patching or dual sync/async support - complete async migration only.

## Executive Summary

The TinyAgent framework is **100% synchronous** with zero async infrastructure. All agent execution loops, tool invocations, API calls, and HTTP requests are blocking. The conversion requires:

1. **OpenAI Client**: Migrate from `OpenAI` to `AsyncOpenAI` (2 locations)
2. **Agent Run Loops**: Convert `ReactAgent.run()` and `TinyCodeAgent.run()` to async (2 files)
3. **Tool Execution**: Add async support to `Tool.run()` and handle mixed sync/async tools (1 core file)
4. **HTTP Requests**: Replace `requests` with `httpx` or `aiohttp` (2 builtin tools)
5. **Tests**: Convert all 13 test files to use `pytest-asyncio` (50+ test methods)
6. **Examples**: Update all 6 demo files to use `async def` and `await` (6 files)

**Total Impact**: 28+ files requiring mechanical changes

---

## Search Commands Used

Research executed via parallel codebase analysis agents:

- Codebase-locator: Found all OpenAI client usage, sync patterns, blocking I/O
- Codebase-analyzer: Analyzed tool execution flow and registry patterns
- Codebase-locator: Mapped test infrastructure and examples

## Findings

### 1. Core Agent Files (2 files - CRITICAL)

#### ReactAgent (`tinyagent/agents/react.py`)
**Current State**: Fully synchronous ReAct loop with blocking OpenAI calls

**Key Locations**:
- Line 19: `from openai import OpenAI` → **CHANGE TO**: `from openai import AsyncOpenAI`
- Line 84: `self.client = OpenAI(api_key=api_key, base_url=base_url)` → **ASYNC INIT**
- Line 98-105: `def run(...)` → **CHANGE TO**: `async def run(...)`
- Line 152: `self._chat(messages, temperature, verbose)` → **ADD AWAIT**
- Line 238-242: Final attempt chat call → **ADD AWAIT**
- Line 285-300: `def _chat(...)` → **CHANGE TO**: `async def _chat(...)`
- Line 291: `self.client.chat.completions.create(...)` → **ADD AWAIT**
- Line 309-339: `def _safe_tool(...)` → **CHANGE TO**: `async def _safe_tool(...)`
- Line 332: `tool.run(args)` → **ADD AWAIT** (requires async Tool.run)

**Execution Pattern**:
```python
# Current (sync)
for step in range(max_steps):
    assistant_reply = self._chat(messages, temperature)
    ok, result = self._safe_tool(name, args)

# Target (async)
for step in range(max_steps):
    assistant_reply = await self._chat(messages, temperature)
    ok, result = await self._safe_tool(name, args)
```

---

#### TinyCodeAgent (`tinyagent/agents/code.py`)
**Current State**: Synchronous Python executor with blocking OpenAI calls

**Key Locations**:
- Line 23: `from openai import OpenAI` → **CHANGE TO**: `from openai import AsyncOpenAI`
- Line 216: `self.client = OpenAI(api_key=api_key, base_url=base_url)` → **ASYNC INIT**
- Line 233-240: `def run(...)` → **CHANGE TO**: `async def run(...)`
- Line 294: `self._chat(messages, verbose)` → **ADD AWAIT**
- Line 396-409: `def _chat(...)` → **CHANGE TO**: `async def _chat(...)`
- Line 400: `self.client.chat.completions.create(...)` → **ADD AWAIT**

**Special Case - PythonExecutor**:
- Line 93-125: `PythonExecutor.run()` executes user code via `exec()` - **KEEP SYNC**
- Tools are injected as raw functions (line 223: `self._executor._globals[name] = tool.fn`)
- **Decision**: Executor stays sync, but tools called from generated code can be async

---

### 2. Tool Registry & Execution (1 file - CRITICAL)

#### Tool Class (`tinyagent/core/registry.py`)
**Current State**: Synchronous tool wrapper with no async detection

**Key Locations**:
- Line 29-44: `Tool` dataclass definition
  - Line 33: `fn: Callable[..., Any]` → **EXTEND TYPE**: `Callable[..., Any] | Coroutine`
  - Line 38-39: `def __call__(...)` → **MAKE ASYNC-AWARE**
  - Line 41-43: `def run(...)` → **MAKE ASYNC-AWARE**

**Required Changes**:
```python
# Current (sync only)
def run(self, payload: Dict[str, Any]) -> str:
    bound = self.signature.bind(**payload)
    return str(self.fn(*bound.args, **bound.kwargs))

# Target (async-aware)
async def run(self, payload: Dict[str, Any]) -> str:
    bound = self.signature.bind(**payload)
    if asyncio.iscoroutinefunction(self.fn):
        result = await self.fn(*bound.args, **bound.kwargs)
    else:
        # Run sync tools in thread pool to avoid blocking
        result = await asyncio.to_thread(self.fn, *bound.args, **bound.kwargs)
    return str(result)
```

**Tool Registration** (Line 54-63):
- Add `import inspect` and `import asyncio` at top
- Line 61: After `signature=inspect.signature(fn)`, add:
  ```python
  is_async=inspect.iscoroutinefunction(fn)
  ```
- Store `is_async` flag in Tool dataclass for runtime checks

---

### 3. Builtin Tools (2 files - HTTP blocking)

#### Web Search (`tinyagent/tools/builtin/web_search.py`)
**Current State**: Uses synchronous `requests.get()` with Brave API

**Key Locations**:
- Line 10: `import requests` → **CHANGE TO**: `import httpx`
- Line 16: `def web_search(query: str) -> str:` → **CHANGE TO**: `async def web_search(...)`
- Line 30-42: `requests.get(...)` → **CHANGE TO**: `async with httpx.AsyncClient() as client: await client.get(...)`

**Pattern**:
```python
# Current (blocking)
response = requests.get("https://api.search.brave.com/res/v1/web/search",
                       headers=headers, params=params, timeout=10)

# Target (async)
async with httpx.AsyncClient() as client:
    response = await client.get("https://api.search.brave.com/res/v1/web/search",
                                headers=headers, params=params, timeout=10)
```

---

#### Web Browse (`tinyagent/tools/builtin/web_browse.py`)
**Current State**: Uses synchronous `requests.get()` to fetch URLs

**Key Locations**:
- Line 8: `import requests` → **CHANGE TO**: `import httpx`
- Line 14: `def web_browse(url: str, ...) -> str:` → **CHANGE TO**: `async def web_browse(...)`
- Line 42: `requests.get(url, headers=headers, timeout=10)` → **CHANGE TO**: `await client.get(...)`

---

#### Planning Tools (`tinyagent/tools/builtin/planning.py`)
**Current State**: Synchronous in-memory storage (no I/O)

**Key Locations**:
- Line 28-40: `create_plan()` → **KEEP SYNC** (pure computation, no I/O)
- Line 44-70: `update_plan()` → **KEEP SYNC** (dictionary operations)
- Line 74-78: `get_plan()` → **KEEP SYNC** (dictionary lookup)

**Decision**: Planning tools can stay sync - they'll be wrapped with `asyncio.to_thread()` automatically by the Tool.run() async wrapper.

---

### 4. Core Infrastructure (4 files - review needed)

#### Finalizer (`tinyagent/core/finalizer.py`)
- Line 12: `import threading` - Uses threading for singleton pattern
- Line 50: `self._lock = threading.Lock()` - Thread-safe but not async-aware
- **Decision**: Keep as-is (threading locks work with asyncio), OR migrate to `asyncio.Lock()`

#### Types (`tinyagent/core/types.py`)
- Line 1-91: All dataclasses - **NO CHANGES NEEDED**
- Pure data structures, no execution logic

#### Exceptions (`tinyagent/core/exceptions.py`)
- Custom exceptions - **NO CHANGES NEEDED**

#### Prompts (`tinyagent/prompts/templates.py` + `loader.py`)
- String templates and file loading - **NO CHANGES NEEDED**

---

### 5. Test Infrastructure (13 files - ALL REQUIRE CHANGES)

#### Configuration Changes Required
**pyproject.toml**:
- Line 89-94: pytest configuration
- **ADD**: `asyncio_mode = "auto"` to `[tool.pytest.ini_options]`
- **ADD**: `pytest-asyncio>=0.23.0` to dependencies (line 18-37)

#### API Integration Tests (4 files)
1. **`tests/api_test/test_agent.py`** (330+ lines, CRITICAL)
   - All test methods → **ADD**: `async def test_*` and `@pytest.mark.asyncio`
   - All `agent.run()` calls → **ADD AWAIT**
   - Mock OpenAI responses stay the same (httpx-compatible)

2. **`tests/api_test/test_agent_advanced.py`**
   - Advanced ReactAgent features → **SAME PATTERN**

3. **`tests/api_test/test_code_agent.py`**
   - TinyCodeAgent tests → **SAME PATTERN**

4. **`tests/api_test/test_web_browse.py`**
   - Web browsing tool tests → **MOCK httpx instead of requests**

#### Unit Tests (9 files)
- **`tests/test_agent_integration.py`** → async test methods
- **`tests/test_exceptions.py`** → likely NO CHANGES (pure exception tests)
- **`tests/test_finalizer.py`** → depends on Finalizer async decision
- **`tests/test_planning_tool.py`** → async test methods (planning tools can stay sync)
- **`tests/test_tool_validation.py`** → NO CHANGES (validation logic stays sync)
- **`tests/test_types.py`** → NO CHANGES (dataclass tests)
- **`tests/prompt_test/test_code_agent.py`** → async test methods
- **`tests/prompt_test/test_file_loader.py`** → NO CHANGES (file I/O is sync)
- **`tests/prompt_test/test_react_agent.py`** → async test methods

**Common Test Pattern**:
```python
# Current (sync)
def test_agent_runs():
    agent = ReactAgent(tools=[get_weather], model="gpt-4o-mini")
    result = agent.run("What's the weather?")
    assert "sunny" in result.lower()

# Target (async)
@pytest.mark.asyncio
async def test_agent_runs():
    agent = ReactAgent(tools=[get_weather], model="gpt-4o-mini")
    result = await agent.run("What's the weather?")
    assert "sunny" in result.lower()
```

---

### 6. Examples & Demos (6 files - ALL REQUIRE CHANGES)

All example files need async conversion:

1. **`examples/simple_demo.py`** - Basic usage
   - Line with `agent.run()` → **ADD AWAIT**
   - Wrap in `asyncio.run()` at module level

2. **`examples/react_demo.py`** - Enhanced features
   - Multiple `agent.run()` calls → **ADD AWAIT**

3. **`examples/code_demo.py`** - Python executor
   - `agent.run()` → **ADD AWAIT**

4. **`examples/file_prompt_demo.py`** - File-based prompts
   - `agent.run()` → **ADD AWAIT**

5. **`examples/jina_reader_demo.py`** - Jina Reader integration
   - `agent.run()` → **ADD AWAIT**

6. **`examples/rpg_demo.py`** - RPG game example
   - `agent.run()` → **ADD AWAIT**

**Common Example Pattern**:
```python
# Current (sync)
if __name__ == "__main__":
    agent = ReactAgent(tools=[get_weather], model="gpt-4o-mini")
    result = agent.run("What's the weather in Tokyo?")
    print(result)

# Target (async)
import asyncio

async def main():
    agent = ReactAgent(tools=[get_weather], model="gpt-4o-mini")
    result = await agent.run("What's the weather in Tokyo?")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 7. Documentation (15+ files - CONTENT UPDATES)

**Files Requiring Code Example Updates**:
- `README.md` - Main usage examples (sync → async)
- `documentation/modules/agent.md` - ReactAgent examples
- `documentation/modules/code_agent.md` - CodeAgent examples
- `documentation/modules/tools.md` - Tool creation examples
- `documentation/examples/basic_usage.md` - Basic examples
- `documentation/examples/advanced.md` - Advanced patterns
- `documentation/examples/setup_andrun.md` - Setup guide

**Update Pattern**: All code blocks showing `agent.run()` need:
1. Add `import asyncio` at top
2. Change `def main():` to `async def main():`
3. Add `await` before `agent.run()`
4. Wrap with `asyncio.run(main())` in `__main__`

---

## Key Patterns / Solutions Found

### Pattern 1: OpenAI Client Migration
**Current**: `from openai import OpenAI` → `self.client = OpenAI(...)`
**Target**: `from openai import AsyncOpenAI` → `self.client = AsyncOpenAI(...)`

**Impact**: 2 files (react.py, code.py)

### Pattern 2: Async Tool Detection
**Current**: No detection - all tools assumed sync
**Target**: Use `inspect.iscoroutinefunction()` during registration

**Implementation**:
```python
# In ToolRegistry.register()
import inspect
import asyncio

tool = Tool(
    fn=fn,
    name=fn.__name__,
    doc=(fn.__doc__ or "").strip(),
    signature=inspect.signature(fn),
    is_async=inspect.iscoroutinefunction(fn)  # NEW
)
```

### Pattern 3: Mixed Sync/Async Tool Execution
**Current**: Direct function call - `tool.fn(*args, **kwargs)`
**Target**: Async-aware wrapper with thread pool for sync tools

**Implementation**:
```python
async def run(self, payload: Dict[str, Any]) -> str:
    bound = self.signature.bind(**payload)
    if self.is_async:
        result = await self.fn(*bound.args, **bound.kwargs)
    else:
        # Run sync tools in thread pool to avoid blocking event loop
        result = await asyncio.to_thread(self.fn, *bound.args, **bound.kwargs)
    return str(result)
```

**Benefit**: Existing sync tools continue working without changes (backward compatible at tool definition level)

### Pattern 4: HTTP Request Migration
**Current**: `requests.get()` (blocking)
**Target**: `httpx.AsyncClient()` (async)

**Impact**: 2 files (web_search.py, web_browse.py)

**Pattern**:
```python
# Current
import requests
response = requests.get(url, headers=headers, timeout=10)

# Target
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get(url, headers=headers, timeout=10)
```

### Pattern 5: Test Async Conversion
**Current**: `def test_*(): agent.run()`
**Target**: `async def test_*(): await agent.run()`

**Impact**: 50+ test methods across 13 files

**Requirements**:
- Add `pytest-asyncio>=0.23.0` to dependencies
- Add `asyncio_mode = "auto"` to pytest config
- Add `@pytest.mark.asyncio` to async test methods (optional with auto mode)

### Pattern 6: Example Async Wrapping
**Current**: Direct script execution
**Target**: `asyncio.run(main())` wrapper

**Impact**: All 6 example files

---

## Knowledge Gaps

### 1. PythonExecutor Async Handling
**Question**: How should TinyCodeAgent handle async tool calls from generated code?

**Current Behavior**:
- Tools injected as raw functions: `self._executor._globals[name] = tool.fn`
- Generated code calls tools directly: `weather = get_weather("Tokyo")`
- Code executed via synchronous `exec(code, ns)`

**Gap**: If `tool.fn` is async, generated code needs `await`:
```python
# Async tool called from generated code
weather = await get_weather("Tokyo")  # Requires top-level await support
```

**Options**:
1. Keep exec() sync, wrap async tools in sync wrappers (defeats purpose)
2. Use `asyncio.run()` wrapper for async tools in sandbox
3. Document that TinyCodeAgent only supports sync tools
4. Migrate to ast-based async code execution

**Decision Needed**: Clarify scope for TinyCodeAgent async support

---

### 2. Finalizer Thread Safety
**Question**: Should Finalizer use `asyncio.Lock()` instead of `threading.Lock()`?

**Current**:
- `threading.Lock()` for singleton pattern (line 50 in finalizer.py)
- Used in both ReactAgent and TinyCodeAgent

**Gap**: Thread locks work with asyncio but are blocking. If multiple async agents run concurrently, `threading.Lock()` could block the event loop.

**Options**:
1. Keep `threading.Lock()` (works but not async-native)
2. Migrate to `asyncio.Lock()` (async-native but changes API)
3. Remove locks (if single-threaded assumption holds)

**Decision Needed**: Clarify concurrency requirements

---

### 3. Backwards Compatibility
**Question**: Should we maintain a sync API wrapper for users who can't migrate?

**Current Plan**: NO - full async migration, no sync patching

**Gap**: Existing users on older codebases may not be able to upgrade

**Options**:
1. **CURRENT**: Breaking change, full async only (cleanest)
2. Provide sync wrapper: `def run_sync(...): return asyncio.run(self.run_async(...))`
3. Maintain separate sync/async agents (doubles maintenance)

**User Decision Required**: Confirm no backwards compatibility needed

---

### 4. Pre-commit Hook Pytest Integration
**Question**: Should pytest be re-enabled in pre-commit hooks?

**Current State**:
- Lines 54-62 in `.pre-commit-config.yaml` are commented out
- Pytest hook was disabled at some point

**Gap**: If async tests are added, pre-commit should verify they pass

**Decision Needed**: Re-enable pytest in pre-commit after async migration?

---

## Mechanical Changes Checklist

### Phase 1: Core Infrastructure (Priority: CRITICAL)
- [ ] `tinyagent/core/registry.py`
  - [ ] Add `is_async: bool` field to Tool dataclass
  - [ ] Add `import inspect, asyncio` at top
  - [ ] Modify `register()` to detect async functions: `is_async=inspect.iscoroutinefunction(fn)`
  - [ ] Convert `Tool.run()` to `async def run()`
  - [ ] Add async-aware execution logic (await async tools, use asyncio.to_thread for sync)
  - [ ] Convert `Tool.__call__()` to async or remove (less commonly used)

### Phase 2: Agent Execution (Priority: CRITICAL)
- [ ] `tinyagent/agents/react.py`
  - [ ] Line 19: Change `from openai import OpenAI` → `from openai import AsyncOpenAI`
  - [ ] Line 84: Change `OpenAI(...)` → `AsyncOpenAI(...)`
  - [ ] Line 98: Change `def run(...)` → `async def run(...)`
  - [ ] Line 152, 238: Add `await` before `self._chat()` calls
  - [ ] Line 285: Change `def _chat(...)` → `async def _chat(...)`
  - [ ] Line 291: Add `await` before `self.client.chat.completions.create(...)`
  - [ ] Line 309: Change `def _safe_tool(...)` → `async def _safe_tool(...)`
  - [ ] Line 332: Add `await` before `tool.run(args)`

- [ ] `tinyagent/agents/code.py`
  - [ ] Line 23: Change `from openai import OpenAI` → `from openai import AsyncOpenAI`
  - [ ] Line 216: Change `OpenAI(...)` → `AsyncOpenAI(...)`
  - [ ] Line 233: Change `def run(...)` → `async def run(...)`
  - [ ] Line 294: Add `await` before `self._chat()`
  - [ ] Line 396: Change `def _chat(...)` → `async def _chat(...)`
  - [ ] Line 400: Add `await` before `self.client.chat.completions.create(...)`

### Phase 3: Builtin Tools (Priority: HIGH)
- [ ] `tinyagent/tools/builtin/web_search.py`
  - [ ] Line 10: Change `import requests` → `import httpx`
  - [ ] Line 16: Change `def web_search(...)` → `async def web_search(...)`
  - [ ] Line 30-42: Replace `requests.get()` with `async with httpx.AsyncClient()` pattern

- [ ] `tinyagent/tools/builtin/web_browse.py`
  - [ ] Line 8: Change `import requests` → `import httpx`
  - [ ] Line 14: Change `def web_browse(...)` → `async def web_browse(...)`
  - [ ] Line 42: Replace `requests.get()` with `await client.get()`

- [ ] `tinyagent/tools/builtin/planning.py`
  - [ ] NO CHANGES (stays sync, wrapped automatically by Tool.run)

### Phase 4: Dependencies (Priority: HIGH)
- [ ] `pyproject.toml`
  - [ ] Add `httpx>=0.27.0` to dependencies (line 18-37)
  - [ ] Add `pytest-asyncio>=0.23.0` to dependencies
  - [ ] Add `asyncio_mode = "auto"` to `[tool.pytest.ini_options]` (line 89-94)
  - [ ] Remove or keep `requests` as optional (check if used elsewhere)

### Phase 5: Tests (Priority: HIGH)
#### API Tests (4 files)
- [ ] `tests/api_test/test_agent.py` - 330+ lines, most critical
  - [ ] Convert all `def test_*` → `async def test_*`
  - [ ] Add `await` before all `agent.run()` calls
  - [ ] Add `@pytest.mark.asyncio` to all test methods
  - [ ] Update mocks to work with AsyncOpenAI (httpx-based)

- [ ] `tests/api_test/test_agent_advanced.py`
  - [ ] Same pattern as test_agent.py

- [ ] `tests/api_test/test_code_agent.py`
  - [ ] Same pattern, test TinyCodeAgent async run

- [ ] `tests/api_test/test_web_browse.py`
  - [ ] Mock httpx instead of requests
  - [ ] Convert test methods to async

#### Unit Tests (9 files)
- [ ] `tests/test_agent_integration.py` → async test methods
- [ ] `tests/test_exceptions.py` → review (likely no changes)
- [ ] `tests/test_finalizer.py` → depends on Finalizer decision
- [ ] `tests/test_planning_tool.py` → async test methods
- [ ] `tests/test_tool_validation.py` → review (validation stays sync)
- [ ] `tests/test_types.py` → no changes (dataclass tests)
- [ ] `tests/prompt_test/test_code_agent.py` → async test methods
- [ ] `tests/prompt_test/test_file_loader.py` → no changes
- [ ] `tests/prompt_test/test_react_agent.py` → async test methods

### Phase 6: Examples (Priority: MEDIUM)
- [ ] `examples/simple_demo.py` → wrap in asyncio.run()
- [ ] `examples/react_demo.py` → wrap in asyncio.run()
- [ ] `examples/code_demo.py` → wrap in asyncio.run()
- [ ] `examples/file_prompt_demo.py` → wrap in asyncio.run()
- [ ] `examples/jina_reader_demo.py` → wrap in asyncio.run()
- [ ] `examples/rpg_demo.py` → wrap in asyncio.run()

### Phase 7: Documentation (Priority: LOW)
- [ ] `README.md` - Update main usage examples
- [ ] `documentation/modules/agent.md` - Update ReactAgent examples
- [ ] `documentation/modules/code_agent.md` - Update CodeAgent examples
- [ ] `documentation/modules/tools.md` - Update tool creation examples
- [ ] `documentation/examples/basic_usage.md` - Update basic examples
- [ ] `documentation/examples/advanced.md` - Update advanced patterns
- [ ] `documentation/examples/setup_andrun.md` - Update setup guide

---

## Testing Strategy

### Baseline Verification
**BEFORE starting changes**:
```bash
source .venv/bin/activate
pytest tests/api_test/test_agent.py -v  # All tests must pass
```

### Incremental Testing
**AFTER each phase**:
```bash
# Phase 1-2: Core changes
pytest tests/test_types.py -v  # Should still pass (no changes)
pytest tests/test_tool_validation.py -v  # Should still pass

# Phase 3-4: After dependencies
pytest tests/api_test/test_agent.py -v  # Will fail until tests updated

# Phase 5: After test migration
pytest tests/api_test/test_agent.py -v  # Should pass with async tests
pytest tests/ -v  # Full suite
```

### Final Validation
```bash
# All tests
pytest tests/ -v

# Pre-commit hooks (if re-enabled)
pre-commit run --all-files

# Linting
ruff check . --fix
ruff format .
```

---

## References

### Core Files Analyzed
- `tinyagent/agents/react.py` - ReactAgent implementation
- `tinyagent/agents/code.py` - TinyCodeAgent implementation
- `tinyagent/core/registry.py` - Tool registration and execution
- `tinyagent/tools/builtin/web_search.py` - Brave Search integration
- `tinyagent/tools/builtin/web_browse.py` - URL fetching tool
- `tinyagent/tools/builtin/planning.py` - Planning tools

### Test Files
- `tests/api_test/test_agent.py` - Main ReactAgent tests (330+ lines)
- `tests/api_test/test_code_agent.py` - TinyCodeAgent tests
- Full list: 13 test files (see section 5)

### Configuration Files
- `pyproject.toml` - pytest configuration and dependencies
- `.pre-commit-config.yaml` - pre-commit hooks

### Documentation
- `CLAUDE.md` - Project workflow and standards
- `README.md` - Main project documentation
- `documentation/modules/*.md` - Module documentation

### External Dependencies
- OpenAI Python SDK: `openai>=1.0` (has AsyncOpenAI)
- httpx: Need to add `httpx>=0.27.0` (async HTTP client)
- pytest-asyncio: Need to add `pytest-asyncio>=0.23.0` (async testing)

---

## Next Steps for Implementation

1. **Resolve Knowledge Gaps** (See section above)
   - Decide: TinyCodeAgent async tool support scope
   - Decide: Finalizer threading vs asyncio locks
   - Confirm: No backwards compatibility needed
   - Decide: Re-enable pytest in pre-commit

2. **Create Implementation Plan** (Use /context-engineer:plan)
   - Break mechanical changes into milestones
   - Define success criteria for each phase
   - Set up validation gates

3. **Execute Changes** (Use /context-engineer:execute)
   - Follow phase order (Core → Agents → Tools → Tests → Examples → Docs)
   - Run tests after each phase
   - Commit atomically per phase

4. **Update KB** (Use claude-kb CLI)
   - Document async migration patterns
   - Create cheatsheet for async tool creation
   - Update component summaries

---

## Appendix: File Inventory Summary

| Category | Count | Async Required |
|----------|-------|----------------|
| Core Agents | 2 | Yes (CRITICAL) |
| Tool Registry | 1 | Yes (CRITICAL) |
| Builtin Tools | 3 | 2 async, 1 stays sync |
| Test Files | 13 | All require changes |
| Examples | 6 | All require changes |
| Documentation | 15+ | Content updates only |
| **TOTAL** | **40+** | **28+ files to modify** |

**Estimated Effort**:
- Mechanical changes: 28 files
- Test updates: 50+ test methods
- Documentation: 15+ files (content only)
- Total LOC impacted: ~3000+ lines
