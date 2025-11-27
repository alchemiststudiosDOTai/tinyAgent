---
date: 2025-11-27T17:01:59-06:00
researcher: Claude
git_commit: 7077f1eb3d83ce00f5fe1b33ac0d0ac5ce2a3349
branch: master
repository: tinyAgent
topic: "Tool System Architecture"
tags: [research, codebase, tools, registry, decorator, agents, global-state]
status: complete
last_updated: 2025-11-27
last_updated_by: Claude
last_updated_note: "Added follow-up research documenting global registry implementation details relevant to proposed removal plan"
---

# Research: Tool System Architecture

**Date**: 2025-11-27T17:01:59-06:00
**Researcher**: Claude
**Git Commit**: 7077f1eb3d83ce00f5fe1b33ac0d0ac5ce2a3349
**Branch**: master
**Repository**: tinyAgent

## Research Question

Map out how the tool system works for tinyagent.

## Summary

The tinyagent tool system provides a decorator-based registration pattern where functions decorated with `@tool` are automatically wrapped in a `Tool` dataclass and stored in a global `ToolRegistry`. Both `ReactAgent` and `TinyCodeAgent` consume tools from this registry during initialization, building internal tool maps. ReactAgent invokes tools via JSON-parsed LLM responses, while TinyCodeAgent injects tool functions directly into an execution namespace for Python code evaluation.

## Detailed Findings

### 1. Core Tool Infrastructure

#### Tool Dataclass

The `Tool` class at [registry.py:30-55](tinyagent/core/registry.py#L30-L55) wraps callables with metadata:

```python
@dataclass(slots=True)
class Tool:
    fn: Callable[..., Any]      # Original function
    name: str                    # Function name
    doc: str                     # Stripped docstring
    signature: inspect.Signature # Parameter signature
    is_async: bool = False       # Async detection
```

Key methods:
- `__call__()` (line 40-41): Direct passthrough invocation
- `run(payload)` (line 43-55): Async-aware execution
  - Async tools: awaited directly
  - Sync tools: executed via `asyncio.to_thread()` to avoid blocking

#### ToolRegistry Class

The `ToolRegistry` at [registry.py:58-106](tinyagent/core/registry.py#L58-L106) implements `MutableMapping[str, Tool]`:

```python
class ToolRegistry(MutableMapping[str, Tool]):
    def __init__(self) -> None:
        self._data: Dict[str, Tool] = {}
        self._frozen: bool = False
```

Features:
- `register()` decorator (lines 66-76): Creates `Tool` wrapper, stores in `_data`
- `freeze()` (lines 99-102): Locks registry using `MappingProxyType`
- `view()` (lines 104-106): Returns read-only mapping

#### Global Registration

At [registry.py:110-111](tinyagent/core/registry.py#L110-L111):

```python
REGISTRY = ToolRegistry()
tool = REGISTRY.register
```

The `@tool` decorator is simply an alias to the global registry's `register` method.

### 2. Tool Registration Flow

When a function is decorated with `@tool`:

```python
@tool
def my_function(x: int) -> str:
    """Description becomes prompt text."""
    return str(x)
```

The `register()` method at [registry.py:66-76](tinyagent/core/registry.py#L66-L76):

1. Checks if registry is frozen (raises `RuntimeError` if so)
2. Creates a `Tool` instance with:
   - `fn`: The original callable
   - `name`: `fn.__name__`
   - `doc`: `(fn.__doc__ or "").strip()`
   - `signature`: `inspect.signature(fn)`
   - `is_async`: `inspect.iscoroutinefunction(fn)`
3. Stores in `self._data[fn.__name__]`
4. Returns the original function unchanged (non-wrapping decorator)

### 3. Built-in Tools

Located in [tinyagent/tools/builtin/](tinyagent/tools/builtin/):

| Tool | File | Type | Description |
|------|------|------|-------------|
| `web_search` | [web_search.py](tinyagent/tools/builtin/web_search.py) | async | Brave Search API integration |
| `web_browse` | [web_browse.py](tinyagent/tools/builtin/web_browse.py) | async | URL fetching with markdown conversion |
| `create_plan` | [planning.py](tinyagent/tools/builtin/planning.py) | sync | In-memory plan creation |
| `update_plan` | [planning.py](tinyagent/tools/builtin/planning.py) | sync | Plan modification |
| `get_plan` | [planning.py](tinyagent/tools/builtin/planning.py) | sync | Plan retrieval |

Example from [web_search.py:15-67](tinyagent/tools/builtin/web_search.py#L15-L67):

```python
@tool
async def web_search(query: str) -> str:
    """Search the web and return a formatted summary of results."""
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    # ... implementation
```

### 4. Agent Tool Consumption

#### ReactAgent Initialization

At [react.py:67-79](tinyagent/agents/react.py#L67-L79):

```python
registry = get_registry()
self._tool_map: dict[str, Tool] = {}

for item in self.tools:
    if isinstance(item, Tool):
        self._tool_map[item.name] = item
    elif callable(item) and item.__name__ in registry:
        self._tool_map[item.__name__] = registry[item.__name__]
    else:
        raise ValueError(f"Invalid tool: {item}")
```

Accepts both:
- Pre-constructed `Tool` objects
- Functions decorated with `@tool` (looked up via registry)

#### TinyCodeAgent Initialization

At [code.py:123-132](tinyagent/agents/code.py#L123-L132):

Same pattern as ReactAgent, plus:
- Async tool rejection (lines 135-140): Raises `ValueError` for async tools
- Tool injection into executor namespace (lines 177-178):
  ```python
  for name, tool in self._tool_map.items():
      self._executor.inject(name, tool.fn)
  ```

### 5. Tool Execution Paths

#### ReactAgent Execution

The main loop at [react.py:98-282](tinyagent/agents/react.py#L98-L282):

1. **LLM Response**: `_chat(messages)` returns JSON-formatted response
2. **JSON Parsing**: `_try_parse_json()` at lines 302-307
3. **Tool Extraction**: Lines 208-209
   ```python
   name = payload.get("tool")
   args = payload.get("arguments", {}) or {}
   ```
4. **Safe Execution**: `_safe_tool()` at [react.py:309-339](tinyagent/agents/react.py#L309-L339)
   - Argument validation via `signature.bind(**args)`
   - Tool execution via `await tool.run(args)`
   - Returns `(success: bool, result: Any)` tuple
5. **Observation Feedback**: Lines 228-231
   ```python
   messages += [
       {"role": "assistant", "content": assistant_reply},
       {"role": "user", "content": f"{tag}: {short}"},
   ]
   ```

#### TinyCodeAgent Execution

The main loop at [code.py:185-345](tinyagent/agents/code.py#L185-L345):

1. **Code Extraction**: `_extract_code()` uses regex to find Python blocks
2. **Executor Run**: `self._executor.run(code)` at line 269
3. **LocalExecutor** at [local.py:144-218](tinyagent/execution/local.py#L144-L218):
   - Import validation via AST parsing
   - Sandboxed `exec(code, self._namespace)` at line 177
   - Tools available as functions in namespace
   - `final_answer()` sentinel detection for completion
4. **Observation Feedback**: Lines 317-326
   ```python
   messages += [
       {"role": "assistant", "content": reply},
       {"role": "user", "content": f"Observation:\n{observation}\n"},
   ]
   ```

### 6. Tool Validation System

Located at [validation.py](tinyagent/tools/validation.py):

The `validate_tool_class()` function at lines 33-73 performs AST-based static analysis:

1. **Class Body** (lines 110-125): Only allows docstrings, functions, pass, assignments
2. **Init Signature** (lines 161-203): Requires literal defaults for all parameters
3. **Method Bodies** (lines 206-213): Validates all referenced names are defined

Violations raise `ToolValidationError` at line 26.

### 7. System Prompts

Tools are injected into system prompts:

**ReactAgent** at [react.py:86-95](tinyagent/agents/react.py#L86-L95):
```python
self._system_prompt = base_prompt.format(
    tools="\n".join(
        f"- {t.name}: {t.doc or '<no description>'} | args={t.signature}"
        for t in self._tool_map.values()
    )
)
```

**TinyCodeAgent** at [code.py:151-154](tinyagent/agents/code.py#L151-L154):
```python
self._system_prompt = base_prompt.format(helpers=", ".join(self._tool_map.keys()))
```

## Architecture Diagram

```
                    User Code
                        |
                   @tool decorator
                        |
                        v
    +-----------------------------------+
    |        ToolRegistry (global)      |
    |  _data: Dict[str, Tool]           |
    |  _frozen: bool                    |
    +-----------------------------------+
                   |
        get_registry() returns view
                   |
        +----------+----------+
        |                     |
        v                     v
+----------------+    +------------------+
|  ReactAgent    |    |  TinyCodeAgent   |
|  _tool_map     |    |  _tool_map       |
+----------------+    +------------------+
        |                     |
        v                     v
 JSON tool calls       Python code with
  via _safe_tool()     injected functions
        |                     |
        v                     v
+----------------+    +------------------+
| Tool.run()     |    | LocalExecutor    |
| - bind args    |    | - exec(code,ns)  |
| - await/thread |    | - direct calls   |
+----------------+    +------------------+
```

## Code References

| Component | File | Lines |
|-----------|------|-------|
| Tool dataclass | `tinyagent/core/registry.py` | 30-55 |
| ToolRegistry class | `tinyagent/core/registry.py` | 58-106 |
| Global REGISTRY | `tinyagent/core/registry.py` | 110-111 |
| ReactAgent tool init | `tinyagent/agents/react.py` | 67-79 |
| ReactAgent _safe_tool | `tinyagent/agents/react.py` | 309-339 |
| TinyCodeAgent tool init | `tinyagent/agents/code.py` | 123-132 |
| LocalExecutor.run | `tinyagent/execution/local.py` | 144-218 |
| Tool validation | `tinyagent/tools/validation.py` | 33-73 |
| Built-in web_search | `tinyagent/tools/builtin/web_search.py` | 15-67 |
| Built-in planning | `tinyagent/tools/builtin/planning.py` | 27-78 |

## Related Files

- [documentation/modules/tools.md](documentation/modules/tools.md) - Comprehensive tools guide
- [documentation/architecture/agents/codeagent-architecture.md](documentation/architecture/agents/codeagent-architecture.md) - TinyCodeAgent architecture
- [examples/react_ai_agent.py](examples/react_ai_agent.py) - ReactAgent with custom tools
- [examples/v2_code_demo.py](examples/v2_code_demo.py) - TinyCodeAgent with custom tools

## Open Questions

None identified.

---

## Follow-up Research: 2025-11-27T17:28:17-06:00

### Context

This follow-up documents the specific aspects of the current tool system implementation relevant to the proposed plan to remove the global registry and have `@tool` return a `Tool` object directly.

### Current Global State Architecture

#### The REGISTRY Singleton

At [registry.py:109-111](tinyagent/core/registry.py#L109-L111):

```python
# Default registry instance + decorator alias
REGISTRY = ToolRegistry()
tool = REGISTRY.register
```

The `tool` decorator is an alias to `REGISTRY.register`, meaning:
- Every `@tool` decoration mutates module-level state
- Tools are registered at import time as a side effect
- The decorated function is returned unchanged (not wrapped)

#### Decorator Return Behavior

The `register()` method at [registry.py:66-76](tinyagent/core/registry.py#L66-L76):

```python
def register(self, fn: Callable[..., Any]) -> Callable[..., Any]:
    if self._frozen:
        raise RuntimeError("Registry is frozen; cannot add new tools.")
    self._data[fn.__name__] = Tool(
        fn=fn,
        name=fn.__name__,
        doc=(fn.__doc__ or "").strip(),
        signature=inspect.signature(fn),
        is_async=inspect.iscoroutinefunction(fn),
    )
    return fn  # <-- Returns original function, NOT the Tool
```

Key observation: The current decorator creates a `Tool` internally but returns the original function. This means:
- `type(decorated_fn)` is `function`, not `Tool`
- The agent must look up the `Tool` object from the registry using the function name

### BaseAgent Registry Dependency

The `_build_tool_map()` method at [base.py:56-73](tinyagent/agents/base.py#L56-L73):

```python
def _build_tool_map(self) -> None:
    registry = get_registry()  # <-- Gets global registry view
    self._tool_map = {}

    for item in self.tools:
        if isinstance(item, Tool):
            self._tool_map[item.name] = item
        elif callable(item) and item.__name__ in registry:
            # Function decorated with @tool - lookup from registry
            self._tool_map[item.__name__] = registry[item.__name__]
        else:
            raise ValueError(f"Invalid tool: {item}")
```

Two code paths exist:
1. **Direct Tool objects**: Stored as-is
2. **Decorated functions**: Looked up from global registry by `__name__`

### No Type Validation at Decoration Time

The current `register()` method performs no validation:
- No type hint checking for parameters
- No return type annotation validation
- No docstring requirement (warning or error)

Validation happens only at execution time when arguments are bound.

### Test Pollution Evidence

From [test_base_agent.py](tests/test_base_agent.py#L13-L16):

```python
@tool
def test_tool(x: int) -> int:
    """Test tool for validation."""
    return x * 2
```

This `@tool` decoration at module load time registers `test_tool` in the global `REGISTRY`. Since tests share the same Python process:
- The tool persists across test runs
- Multiple test modules can have name collisions
- Cleanup would require `REGISTRY._data.clear()` between tests

### Public API Exports

At [core/__init__.py:5](tinyagent/core/__init__.py#L5):
```python
from .registry import Tool, freeze_registry, get_registry, tool
```

At [tinyagent/__init__.py:54-56](tinyagent/__init__.py#L54-L56):
```python
freeze_registry,
get_registry,
tool,
```

Public API currently exports:
- `tool` - the decorator
- `Tool` - the dataclass
- `get_registry()` - read-only registry view
- `freeze_registry()` - locks registry

### Example Tool Definitions

From [code_agent_demo.py:27-32](examples/code_agent_demo.py#L27-L32):

```python
@tool
def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number recursively."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
```

From [react_ai_agent.py:25-62](examples/react_ai_agent.py#L25-L62):

```python
@tool
def ddgs_search(query: str, max_results: int = 5) -> str:
    """Search the web using DDGS metasearch."""
    # ...
```

Both examples pass the decorated function directly to agents:
```python
agent = TinyCodeAgent(tools=[fibonacci, factorial], ...)
agent = ReactAgent(tools=[ddgs_search, generate_report], ...)
```

### Freeze Registry Feature

At [registry.py:99-102](tinyagent/core/registry.py#L99-L102):

```python
def freeze(self) -> None:
    """Lock the registry against further changes."""
    self._frozen = True
    self._data = MappingProxyType(self._data)  # type: ignore[assignment]
```

This feature:
- Converts `_data` dict to immutable `MappingProxyType`
- Prevents new tool registration after freeze
- Raises `RuntimeError` on subsequent `register()` calls

### Summary of Current State vs Proposed Changes

| Aspect | Current Implementation | Proposed Change |
|--------|----------------------|-----------------|
| Decorator return | Returns original `function` | Returns `Tool` object |
| Registration | Mutates global `REGISTRY` | No global state |
| Type validation | None at decoration time | Fail-fast at decoration time |
| Docstring | No requirement | Warning if missing |
| Test cleanup | Requires `REGISTRY._data.clear()` | No cleanup needed |
| Agent tool lookup | Via registry by `__name__` | Direct `isinstance(item, Tool)` check |
| `get_registry()` | Returns read-only view | To be removed |
| `freeze_registry()` | Locks global state | To be removed |
