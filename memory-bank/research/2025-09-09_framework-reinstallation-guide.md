---
title: "Framework Reinstallation After Agent File Movement"
date: "2025-09-09"
author: "Claude"
phase: "Research"
tags: ["venv", "setup", "imports", "package-structure"]
last_updated: "2025-09-09 12:01:00"
last_updated_by: "Claude"
git_commit: "rewrite"
---

# Research – Framework Reinstallation After Agent File Movement

**Date:** 2025-09-09
**Owner:** Claude
**Phase:** Research

## Goal
Document the current state of the codebase after moving `agent.py` and `code_agent.py` to `tinyagent/agents/` and outline the steps needed to reinstall the venv correctly.

## Current State

### File Movement Status
- `agent.py` moved from `tinyagent/` to `tinyagent/agents/` ✓
- `code_agent.py` moved from `tinyagent/` to `tinyagent/agents/` ✓
- **Missing**: `tinyagent/agents/__init__.py` file

### Import Issues Identified

#### 1. Broken Main Package Imports
**File**: `tinyagent/__init__.py`
```python
from .agent import ReactAgent                    # BROKEN - file moved
from .code_agent import PythonExecutor, TinyCodeAgent  # BROKEN - file moved
```

#### 2. Missing Package Structure
The `tinyagent/agents/` directory lacks an `__init__.py` file, making it an implicit namespace package rather than a proper Python subpackage.

#### 3. Relative Import Updates Needed
Both agent files need relative import updates:
- `agents/agent.py`: `from .prompt import ...` → `from ..prompt import ...`
- `agents/agent.py`: `from .tools import ...` → `from ..tools import ...`
- `agents/code_agent.py`: Similar updates needed

## Files Requiring Updates

### Critical (Framework won't work without these)
1. **`tinyagent/__init__.py`** - Update import paths to `from .agents.agent import ...`
2. **`tinyagent/agents/__init__.py`** - Create this file to expose agent classes
3. **`tinyagent/agents/agent.py`** - Update relative imports to use `..`
4. **`tinyagent/agents/code_agent.py`** - Update relative imports to use `..`

### Test Files (Will fail until fixed)
1. **`tests/api_test/test_agent.py`** - Update `from tinyagent.agent import ...`
2. **`tests/api_test/test_code_agent.py`** - Update `from tinyagent.code_agent import ...`
3. **`tests/api_test/test_agent_advanced.py`** - Update imports

### Documentation Files
1. **`CLAUDE.md`** - Update project map and import examples
2. **Documentation files** - Update import examples throughout

## Venv Reinstallation Protocol

### Before Reinstallation - MUST FIX FIRST
1. Create `tinyagent/agents/__init__.py` with proper exports
2. Update `tinyagent/__init__.py` to import from new locations
3. Fix relative imports in both agent files
4. Update test file imports

### Reinstallation Steps

#### Option A: UV (Recommended - 10x Faster)
```bash
# 1. Remove existing venv completely
rm -rf .venv

# 2. Create fresh venv
uv venv

# 3. Activate environment
source .venv/bin/activate

# 4. Install project in development mode
uv pip install -e .

# 5. Install development dependencies
uv pip install pytest pre-commit ruff

# 6. Install pre-commit hooks
pre-commit install
```

#### Option B: Traditional venv
```bash
# 1. Remove existing venv completely
rm -rf venv

# 2. Create fresh venv
python3 -m venv venv

# 3. Activate environment
source venv/bin/activate

# 4. Install project in development mode
pip install -e .

# 5. Install development dependencies
pip install pytest pre-commit ruff
```

### Verification Commands After Reinstallation
```bash
# Test basic imports work
python -c "from tinyagent import ReactAgent, TinyCodeAgent; print('Success')"

# Run test suite
pytest tests/api_test/test_agent.py -v

# Test examples
python examples/react_demo.py
python examples/code_demo.py

# Check linting
ruff check . --fix
ruff format .
```

## Package Configuration Impact

The `pyproject.toml` uses `packages = ["tinyagent"]` which automatically discovers packages. This configuration is correct and doesn't need changes - the issue is purely at the import level within the package.

## Working Files (No Changes Needed)
- All example files use `from tinyagent import ...` which will work once main init is fixed
- `tools.py` and `prompt.py` remain in place and work correctly
- `base_tools/` directory structure is intact

## Knowledge Gaps
- Current status of existing venv (whether it's .venv or venv)
- Whether any other files were moved during the reorganization
- Current working branch status and whether changes are committed

## References
- File: `tinyagent/__init__.py` - Main package exports
- File: `pyproject.toml` - Package configuration
- File: `examples/react_demo.py` - Example usage
- File: `CLAUDE.md` - Development workflow instructions
