# Research – TinyCodeAgent Architecture for Rebuild

**Date:** 2025-11-25
**Owner:** Claude Agent
**Phase:** Research

## Goal

Comprehensively map the current TinyCodeAgent implementation before rebuilding. Document architecture, security model, integration points, and gaps to inform redesign decisions.

---

## Findings

### Core Implementation Files

| File | Purpose | Lines |
|------|---------|-------|
| [tinyagent/agents/code.py](tinyagent/agents/code.py) | Main implementation: `FinalResult`, `PythonExecutor`, `TinyCodeAgent` | ~422 |
| [tinyagent/__init__.py](tinyagent/__init__.py) | Public API exports | Line 1, 16 |
| [tinyagent/agents/__init__.py](tinyagent/agents/__init__.py) | Subpackage exports | Lines 3, 6 |

### Example Files

| File | Purpose |
|------|---------|
| [examples/code_demo.py](examples/code_demo.py) | Primary TinyCodeAgent demo |
| [examples/file_prompt_demo.py](examples/file_prompt_demo.py) | Custom prompt loading demo |

### Documentation Files

| File | Purpose |
|------|---------|
| [documentation/modules/code_agent.md](documentation/modules/code_agent.md) | API reference |
| [documentation/python_execution_comparison.md](documentation/python_execution_comparison.md) | tinyagent vs smolagents analysis |

---

## Architecture Overview

### Class Hierarchy

```
FinalResult (dataclass)          # Lines 39-44 - Sentinel for final_answer()
    └── value: Any

PythonExecutor                   # Lines 46-157 - Sandboxed Python execution
    ├── SAFE_BUILTINS            # Lines 49-71 - Whitelist of 21 builtins
    ├── __init__(extra_imports)  # Lines 73-91 - Sandbox construction
    ├── run(code) -> (str, bool) # Lines 93-125 - Execute code
    ├── _check_imports(code)     # Lines 143-156 - AST-based import validation
    ├── _safe_import()           # Lines 127-132 - Runtime import guard
    └── _final_answer(value)     # Lines 134-141 - Frame-based sentinel storage

TinyCodeAgent (dataclass)        # Lines 159-422 - LLM orchestration layer
    ├── __post_init__()          # Lines 193-240 - Tool validation + injection
    ├── run(task) -> str         # Lines 242-398 - Async ReAct loop
    ├── _chat(messages)          # Lines 400-413 - LLM API call
    └── _extract_code(text)      # Lines 415-421 - Regex code extraction
```

**Note:** TinyCodeAgent does NOT inherit from ReactAgent - independent implementation.

---

## Security Model Analysis

### Two-Layer Defense Architecture

#### Layer 1: AST Static Analysis (Pre-execution)
**Location:** [code.py:143-156](tinyagent/agents/code.py#L143-L156)

```python
def _check_imports(self, code: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # Validates top-level module against whitelist
        elif isinstance(node, ast.ImportFrom):
            # Validates from X import Y patterns
```

**Catches:** `import os`, `from os import path`, `import subprocess`

#### Layer 2: Runtime Import Guard
**Location:** [code.py:127-132](tinyagent/agents/code.py#L127-L132)

```python
def _safe_import(self, name, *args, **kwargs):
    module_name = name.split(".")[0]
    if module_name not in self._allowed:
        raise RuntimeError(f"Import '{name}' not allowed")
    return __import__(name, *args, **kwargs)
```

**Catches:** Dynamic imports that bypass AST analysis

### SAFE_BUILTINS Whitelist

**Location:** [code.py:49-71](tinyagent/agents/code.py#L49-L71)

```python
SAFE_BUILTINS = {
    "abs", "all", "any", "bool", "dict", "enumerate",
    "float", "int", "len", "list", "max", "min",
    "print", "range", "round", "sorted", "str",
    "sum", "tuple", "type", "zip",
}
```

**Excluded dangerous builtins:** `eval`, `exec`, `open`, `compile`, `__import__` (replaced), `getattr`, `setattr`, `delattr`, `globals`, `locals`, `vars`

### Security Gaps (from comparison doc)

| Vulnerability | Status | Mitigation Needed |
|--------------|--------|-------------------|
| Memory exhaustion attacks | Not protected | Add resource limits |
| CPU exhaustion attacks | Not protected | Add execution timeout |
| Infinite loops | Not protected | Add step/time limits |
| Network access | Not controlled | OS-level or container isolation |
| Filesystem access | Partially blocked | `open` not in builtins, but workarounds exist |

---

## Tool Integration Mechanism

### Injection Flow

```
1. @tool decorator creates Tool(fn=original_function, ...)
2. TinyCodeAgent.__post_init__ validates tools (lines 194-220)
3. Async tools rejected (lines 214-220) - exec() can't handle async
4. Tool functions injected into executor namespace (line 232):

   self._executor._globals[name] = tool.fn

5. LLM writes: search("query")
6. exec() resolves 'search' from namespace → calls actual function
```

### Namespace Structure After Init

```python
self._executor._globals = {
    "__builtins__": {
        # 21 safe builtins + _safe_import
    },
    "final_answer": <bound method _final_answer>,
    "tool_name_1": <function>,
    "tool_name_2": <function>,
    # ... injected tools
}
```

---

## Final Answer Sentinel Pattern

### Why Frame Manipulation?

**Problem:** `exec()` runs in isolated namespace. Normal assignment in `_final_answer` wouldn't persist.

**Solution:** [code.py:134-141](tinyagent/agents/code.py#L134-L141)

```python
def _final_answer(self, value):
    import inspect
    frame = inspect.currentframe().f_back  # Get caller's frame
    frame.f_globals["_final_result"] = FinalResult(value)  # Write to exec namespace
    return value
```

**Detection:** [code.py:120-121](tinyagent/agents/code.py#L120-L121)

```python
if "_final_result" in ns and isinstance(ns["_final_result"], FinalResult):
    return str(ns["_final_result"].value), True
```

---

## Execution Loop Architecture

### ReAct-Style Flow

```
┌─────────────────────────────────────────────────────────┐
│                    TinyCodeAgent.run()                   │
├─────────────────────────────────────────────────────────┤
│  1. Initialize messages with system prompt + task       │
│  2. FOR step in range(max_steps):                       │
│     │                                                   │
│     ├─► 3. Call LLM (_chat)                            │
│     │                                                   │
│     ├─► 4. Extract Python code block (_extract_code)   │
│     │   └── No code? Request retry with user message   │
│     │                                                   │
│     ├─► 5. Execute code (executor.run)                 │
│     │   ├── KeyError? Add docstring hints, retry       │
│     │   └── Other error? Report to LLM, retry          │
│     │                                                   │
│     ├─► 6. Check if done (final_answer called)         │
│     │   └── Yes? Return result                         │
│     │                                                   │
│     └─► 7. Add observation to messages, continue       │
│                                                         │
│  8. Step limit reached → raise StepLimitReached        │
└─────────────────────────────────────────────────────────┘
```

### Error Recovery Strategy

| Error Type | Handling | Location |
|------------|----------|----------|
| No code block | Request Python block | Lines 310-318 |
| KeyError (tool params) | Add docstring hints | Lines 331-343 |
| General exception | Report error message | Lines 344-352 |
| Step limit | Raise/return error | Lines 382-398 |

---

## Key Patterns / Solutions Found

### 1. Namespace Isolation Pattern
**Location:** [code.py:114](tinyagent/agents/code.py#L114)
```python
ns = self._globals.copy()  # Fresh copy per execution
```
Prevents cross-execution state pollution.

### 2. Sentinel Return Pattern
Using `FinalResult` dataclass + frame manipulation vs string parsing. Type-safe completion detection.

### 3. Temperature=0 Enforcement
**Location:** [code.py:407](tinyagent/agents/code.py#L407)
Always deterministic code generation to reduce syntax errors.

### 4. Async Tool Rejection
**Location:** [code.py:214-220](tinyagent/agents/code.py#L214-L220)
Hard constraint due to `exec()` limitation. Forces sync-only tools.

---

## Comparison: tinyagent vs smolagents

| Aspect | tinyagent | smolagents |
|--------|-----------|------------|
| Sandbox Type | AST + restricted globals | Multiple (local, Docker, E2B) |
| Security Level | Basic | Enterprise-grade |
| Code Size | ~110 lines | 300+ lines |
| Execution Model | Direct exec() | Abstracted executors |
| Resource Limits | None | Memory, CPU, time limits |
| Async Tools | Not supported | Supported |
| Session Reset | Per-execution copy | Explicit restart_session() |

### smolagents Features Missing in tinyagent

1. **Docker isolation** - Container-based execution with resource limits
2. **E2B cloud sandbox** - Cloud-based isolation
3. **Execution timeouts** - Hard 30-second limits
4. **Memory limits** - Container mem_limit
5. **Session management** - restart_session() for clean state
6. **Structured output** - PythonToolOutput dataclass

---

## Knowledge Gaps

### Missing Information

1. **Performance benchmarks** - No actual benchmarks in codebase, only comparison doc estimates
2. **Production deployment patterns** - How to add real resource limits?
3. **Builtins bypass vulnerabilities** - Are there known bypasses for current implementation?
4. **Tool state management** - How to handle stateful tools across steps?

### Test Coverage Issues (Critical)

**Current state:** 88% of tests deleted (from ~2,649 lines to ~41 lines)

**Missing test coverage:**
- TinyCodeAgent run() method
- PythonExecutor security tests
- Tool injection tests
- Error handling paths
- Final answer detection
- Import validation

---

## Recommendations for Rebuild

### Priority 1: Security Hardening

1. Add execution timeout using `signal.alarm()` or threading
2. Add memory limit tracking
3. Consider optional Docker/subprocess isolation mode
4. Audit builtins bypass vectors

### Priority 2: Architecture Improvements

1. Abstract executor interface (like smolagents) for pluggable backends
2. Add structured output type (`CodeExecutionResult`)
3. Consider async tool support with different execution strategy
4. Add session reset capability

### Priority 3: Testing

1. Restore comprehensive test suite
2. Add security-focused tests (fuzzing, bypass attempts)
3. Add performance benchmarks

---

## References

- [tinyagent/agents/code.py](tinyagent/agents/code.py) - Main implementation
- [documentation/python_execution_comparison.md](documentation/python_execution_comparison.md) - Detailed comparison
- [documentation/modules/code_agent.md](documentation/modules/code_agent.md) - API reference
- [examples/code_demo.py](examples/code_demo.py) - Usage example
