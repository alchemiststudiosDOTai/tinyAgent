# tinyAgent-t3i, tinyAgent-qdh, tinyAgent-cvf: Refactor Agent run() God Methods

**Date:** 2025-12-31

## Problem Statement

Both `ReactAgent.run()` (176 lines) and `TinyCodeAgent.run()` (177 lines) are god methods with:
- Multiple responsibilities (initialization, LLM interaction, response parsing, tool execution, pruning)
- Deep nesting (up to 4-5 levels)
- Difficult to test individual components
- Hard to understand and maintain

## Locations with Issues

### ReactAgent (tinyagent/agents/react.py:102-277)
- Lines 124-141: Initialization and logging setup
- Lines 142-234: Main step loop with nested conditionals
- Lines 236-277: Final attempt logic

### TinyCodeAgent (tinyagent/agents/code.py:189-365)
- Lines 221-257: Initialization and logging setup
- Lines 259-347: Main step loop with nested conditionals
- Lines 349-365: Error handling

## Implementation Plan

### Phase 1: Extract Initialization Logic
1. Create `_initialize_run()` method in ReactAgent
2. Create `_initialize_run()` method in TinyCodeAgent
3. Extract logging banner setup into its own method

### Phase 2: Extract Step Processing Logic
1. Create `_process_step()` method in ReactAgent to handle each iteration
2. Create `_process_step()` method in TinyCodeAgent to handle each iteration
3. Extract response handling into `_handle_response()`

### Phase 3: Reduce Deep Nesting with Early Returns
1. Use early returns when payload parsing fails
2. Use early returns when scratchpad-only responses occur
3. Use early returns when tool execution completes

### Phase 4: Extract Final Attempt Logic (ReactAgent only)
1. Create `_attempt_final_answer()` method
2. Extract result return logic into `_build_result()`

## Success Criteria
- [ ] Each run() method under 100 lines
- [ ] Maximum nesting depth of 3 levels
- [ ] All extracted methods are private (start with _)
- [ ] Tests pass (pytest tests/api_test/test_agent.py -v)
- [ ] Ruff linting passes
- [ ] No functional changes (same behavior as before)
