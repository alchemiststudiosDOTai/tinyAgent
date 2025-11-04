# Research – Requests Import Error After PR Removing Request Shim

**Date:** 2025-11-04 11:34:55
**Owner:** context-engineer:research
**Phase:** Research
**Git Commit:** c2e98b45952869b2e6a43325da60c8b2f058a028
**Branch:** master

## Goal

Analyze the ImportError affecting all tests after a recent PR removed the `requests` dependency from `pyproject.toml`. The error occurs during test module imports when `tinyagent/tools/builtin/web_search.py` tries to import the `requests` library, which is no longer installed.

## Error Symptoms

All test files fail at import time with:
```
ModuleNotFoundError: No module named 'requests'
  at tinyagent/tools/builtin/web_search.py:10
```

Affected test files (10 total):
- `tests/api_test/test_agent.py`
- `tests/api_test/test_agent_advanced.py`
- `tests/api_test/test_code_agent.py`
- `tests/prompt_test/test_code_agent.py`
- `tests/prompt_test/test_react_agent.py`
- `tests/test_agent_integration.py`
- `tests/test_exceptions.py`
- `tests/test_finalizer.py`
- `tests/test_tool_validation.py`
- `tests/test_types.py`

## Findings

### Root Cause Analysis

#### 1. Dependency Removal
- **File:** `pyproject.toml`
- **What changed:** Git history shows `requests>=2.31.0` was removed from dependencies
- **Previous state:**
  ```toml
  dependencies = [
      "python-dotenv>=1.0.0",
      "requests>=2.31.0",
      "openai>=1.0.0",
      ...
  ]
  ```
- **Current state:**
  ```toml
  dependencies = [
      "openai>=1.0",
      "pytest>=8.0",
      "pre-commit>=4.0",
      "python-dotenv>=1.0",
  ]
  ```

#### 2. Import Chain Failure
The error occurs due to eager loading of builtin tools:

```
tests/test_*.py
  ↓ from tinyagent import ...
tinyagent/__init__.py:14
  ↓ from .tools import ToolValidationError, validate_tool_class
tinyagent/tools/__init__.py:3
  ↓ from .builtin import create_plan, get_plan, update_plan, web_search
tinyagent/tools/builtin/__init__.py:4
  ↓ from .web_search import web_search
tinyagent/tools/builtin/web_search.py:10
  ↓ import requests  # ❌ FAILS HERE
```

### Relevant Files & Their Roles

1. **`tinyagent/tools/builtin/web_search.py:10`** → Imports `requests` unconditionally
   - Implements `@tool` decorated function for Brave Search API
   - Uses `requests.get()` for HTTP calls (line 30)
   - Uses `response.status_code`, `response.json()`, and exception handling (lines 44, 47, 65)
   - Only example using it: `examples/web_search_tool.py`

2. **`tinyagent/tools/builtin/__init__.py:4`** → Exports web_search eagerly
   ```python
   from .web_search import web_search
   ```

3. **`tinyagent/tools/__init__.py:3`** → Re-exports builtin tools
   ```python
   from .builtin import create_plan, get_plan, update_plan, web_search
   ```

4. **`tinyagent/__init__.py:14`** → Imports from tools package
   ```python
   from .tools import ToolValidationError, validate_tool_class
   ```

5. **`pyproject.toml:24-29`** → Missing `requests` in dependencies

6. **`documentation/examples/advanced.md:10`** → Example code shows `import requests` pattern

### Builtin Tools Architecture

**All builtin tools:**
- `web_search` (web_search.py) → **Requires `requests`** ⚠️
- `create_plan` (planning.py) → Standard library only ✓
- `get_plan` (planning.py) → Standard library only ✓
- `update_plan` (planning.py) → Standard library only ✓

**Registration pattern:**
- All tools use `@tool` decorator from `tinyagent.core.registry`
- Decorator executes at import time (eager registration)
- No lazy loading mechanism exists
- Global registry: `REGISTRY = ToolRegistry()`

### Optional Dependency Patterns in Codebase

**Pattern observed in all examples:** Try/except for dotenv
```python
# From examples/simple_demo.py:14-19, react_demo.py:12-17, etc.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, skip
```

**No optional dependency groups in pyproject.toml:**
- No `[project.optional-dependencies]` section
- No extras_require pattern (e.g., `pip install tinyagent[search]`)

**Inconsistency:** `python-dotenv` is declared as hard dependency but examples treat it as optional

## Key Patterns / Solutions Found

### Solution Option 1: Make `web_search` Optional via Lazy Import

**Pattern:** Conditional import with try/except in `tinyagent/tools/builtin/__init__.py`

```python
# In tinyagent/tools/builtin/__init__.py
from .planning import create_plan, get_plan, update_plan

try:
    from .web_search import web_search
    __all__ = ["create_plan", "get_plan", "update_plan", "web_search"]
except ImportError:
    __all__ = ["create_plan", "get_plan", "update_plan"]
    # web_search not available without requests
```

**Pros:**
- Maintains backward compatibility for users who have `requests` installed
- Minimal code changes
- No pyproject.toml changes needed

**Cons:**
- Silent failure if user expects web_search but doesn't have requests
- Needs propagation to `tinyagent/tools/__init__.py:3` as well

### Solution Option 2: Optional Dependency Group

**Pattern:** Add extras_require to pyproject.toml

```toml
[project.optional-dependencies]
search = ["requests>=2.31.0"]
all = ["requests>=2.31.0"]
```

Install with: `pip install tinyagent[search]`

**Pros:**
- Standard Python packaging practice
- Clear documentation of optional features
- Users can opt-in to web search functionality

**Cons:**
- Requires lazy import pattern (Solution 1) anyway
- Breaking change for users who expect web_search to always be available

### Solution Option 3: Separate web_search into Plugin/Extension

**Pattern:** Move web_search to examples or separate package

```
tinyagent/
  tools/
    builtin/
      planning.py  # Core builtin tools
examples/
  tools/
    web_search.py  # Optional tool users can import if needed
```

**Pros:**
- Clean separation of core vs. optional functionality
- No import-time failures
- Clear that web_search is an example, not core feature

**Cons:**
- Breaking change for existing users
- More complex user imports

### Solution Option 4: Re-add `requests` as Hard Dependency

**Pattern:** Restore `requests>=2.31.0` to pyproject.toml dependencies

```toml
dependencies = [
    "openai>=1.0",
    "pytest>=8.0",
    "pre-commit>=4.0",
    "python-dotenv>=1.0",
    "requests>=2.31.0",  # Re-add for web_search tool
]
```

**Pros:**
- Simplest fix, immediate resolution
- No code changes needed
- No breaking changes

**Cons:**
- Adds dependency even for users who don't need web search
- Reverses the original intent of the PR

## Knowledge Gaps

1. **Why was `requests` removed?** - The motivation for removing `requests` in the recent PR is unclear. Was it to reduce dependency bloat, security concerns, or preparation for a different HTTP client?

2. **Is `web_search` a core feature?** - Need to determine if web_search is intended as a core builtin tool or an optional example tool for users to reference.

3. **Test coverage for web_search** - No tests found for web_search functionality. Is this tool tested? Should it be?

4. **User impact assessment** - How many users rely on `web_search` being available by default? Are there public APIs or documentation that promise web_search availability?

5. **Future of builtin tools** - Are there plans to add more builtin tools with external dependencies? If so, the architecture should support optional dependencies systematically.

## Additional Search Recommendations

To gather more context:
- `grep -ri "web_search" .claude/` - Check knowledge base for web_search context
- `git log --all -p pyproject.toml | grep -A 10 -B 10 requests` - Full history of requests dependency
- Check GitHub issues/PRs for discussions about dependency management
- Review commit messages around the time `requests` was removed

## References

### Source Files
- [tinyagent/tools/builtin/web_search.py](tinyagent/tools/builtin/web_search.py) - Web search implementation
- [tinyagent/tools/builtin/__init__.py](tinyagent/tools/builtin/__init__.py) - Builtin exports
- [tinyagent/tools/__init__.py](tinyagent/tools/__init__.py) - Tools package exports
- [tinyagent/__init__.py](tinyagent/__init__.py) - Main package imports
- [pyproject.toml](pyproject.toml) - Project dependencies

### Examples
- [examples/web_search_tool.py](examples/web_search_tool.py) - Only usage of web_search
- [documentation/examples/advanced.md](documentation/examples/advanced.md) - Advanced patterns

### Test Files (All failing)
- [tests/api_test/test_agent.py](tests/api_test/test_agent.py)
- [tests/api_test/test_agent_advanced.py](tests/api_test/test_agent_advanced.py)
- [tests/test_agent_integration.py](tests/test_agent_integration.py)
- Plus 7 other test files

## Recommended Next Steps

1. **Immediate fix (choose one):**
   - **Option A (Quick):** Re-add `requests>=2.31.0` to dependencies if web_search is core
   - **Option B (Better):** Implement lazy import pattern (Solution 1) to make web_search optional

2. **Long-term improvements:**
   - Define clear policy: which builtin tools are "core" vs "optional"
   - Add `[project.optional-dependencies]` for optional features
   - Document which dependencies are required for which features
   - Consider adding tests for web_search or removing it from builtin

3. **Documentation updates:**
   - Update README.md to clarify optional dependencies
   - Add installation instructions for optional features
   - Update examples to handle missing optional dependencies gracefully
