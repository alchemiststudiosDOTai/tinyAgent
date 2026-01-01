# tinyAgent-4gh: Fix pre-existing mypy type errors for optional types

**Date:** 2025-12-31

## Problem Statement
The codebase has 60+ mypy errors related to optional types (`MemoryManager | None`, `AgentLogger | None`) not being narrowed before use. These fields are guaranteed to be non-None after `__post_init__` but mypy cannot infer this.

## Locations with Issues

### tinyagent/agents/base.py
- Line 45: `logger: AgentLogger | None = None` - Initialized in `__post_init__` line 50-51
- Used on all subclass methods (ReactAgent, TinyCodeAgent) without None checks

### tinyagent/agents/react.py
- Line 77: `memory: MemoryManager | None = field(default=None)` - Initialized in `__post_init__` line 98-99
- 30+ mypy errors where `self.memory` methods are called without None check

### tinyagent/agents/code.py
- Line 124: `memory_manager: MemoryManager | None = field(default=None)` - Initialized in `__post_init__` line 159-160
- 25+ mypy errors where `self.memory_manager` methods are called without None check

## Implementation Plan

### Phase 1: Fix BaseAgent.logger
1. Change `logger: AgentLogger | None = None` to `logger: AgentLogger = field(init=False)`
2. Set default value in `__post_init__` (already done, just needs type change)

### Phase 2: Fix ReactAgent.memory
1. Change `memory: MemoryManager | None = field(default=None)` to `memory: MemoryManager = field(init=False)`
2. Set default value in `__post_init__` (already done, just needs type change)

### Phase 3: Fix TinyCodeAgent.memory_manager
1. Change `memory_manager: MemoryManager | None = field(default=None)` to `memory_manager: MemoryManager = field(init=False)`
2. Set default value in `__post_init__` (already done, just needs type change)

### Phase 4: Quality Control
1. Run mypy to verify all 60 errors are resolved
2. Run ruff check and format
3. Run pytest to ensure no runtime breakage

## Success Criteria
- [ ] All 60 mypy errors resolved
- [ ] ruff check passes
- [ ] pytest tests pass
- [ ] No runtime behavior changes

## Technical Notes
Using `field(init=False)` signals to dataclass that this field is not part of `__init__` parameters but will be set during initialization. This is the recommended pattern for fields set in `__post_init__`.
