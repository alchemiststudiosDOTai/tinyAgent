# Research: ReactAgent Refactoring Analysis

**Date:** 2026-01-02
**Owner:** Agent
**Phase:** Research
**Branch:** tooling
**Commit:** 9b8d716

## Goal

Validate the claims in PLAN.md regarding ReactAgent refactoring needs. Analyze `_process_step` complexity, identify code duplication between ReactAgent and TinyCodeAgent, and confirm architectural issues.

## Findings

### File Locations

| Component | Path | Line |
|-----------|------|------|
| ReactAgent class | `tinyagent/agents/react.py` | 51 |
| TinyCodeAgent class | `tinyagent/agents/code.py` | 67 |
| BaseAgent class | `tinyagent/agents/base.py` | 28 |
| ReactAgent._process_step | `tinyagent/agents/react.py` | 172 |
| TinyCodeAgent._process_step | `tinyagent/agents/code.py` | 255 |
| ScratchpadStep.to_messages | `tinyagent/memory/steps.py` | 171 |
| AgentMemory | `tinyagent/memory/scratchpad.py` | 19 |

### Confirmed Issues from PLAN.md

#### 1. Seven Responsibilities in `_process_step` (CONFIRMED)

Location: `tinyagent/agents/react.py:172-224`

| Responsibility | Line | Description |
|----------------|------|-------------|
| Memory Serialization | 188 | `messages = self.memory.to_messages()` |
| LLM Communication | 189 | `assistant_reply = await self._chat(messages, temperature)` |
| Response Parsing | 191-194 | `payload = self._adapter.extract_tool_call(assistant_reply)` |
| Argument Validation | 196-203 | `validation = self._adapter.validate_tool_call(...)` |
| Scratchpad Handling | 205-208 | `if SCRATCHPAD_KEY in payload: self._handle_scratchpad(...)` |
| Final Answer Detection | 211-215 | `if ANSWER_KEY in payload: ...` |
| Tool Execution | 218-223 | `tool_result = await self._execute_tool(...)` |

**Cyclomatic Complexity:** 8 (7 decision points + 1 for method entry)

#### 2. Scratchpad Role Continuity Issue (CONFIRMED)

Location: `tinyagent/memory/steps.py:171-184`

```python
def to_messages(self) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if self.raw_llm_response:
        messages.append({"role": "assistant", "content": self.raw_llm_response})
    messages.append({"role": "user", "content": f"Scratchpad noted: {self.content}"})
    return messages
```

**Problem:** Injects synthetic `user` messages, breaking LLM role continuity (assistant -> user -> assistant pattern).

#### 3. Unbounded Temperature (CONFIRMED)

Location: `tinyagent/agents/react.py:159-160`

```python
if increment_temp:
    temperature += TEMP_STEP  # TEMP_STEP = 0.2 (line 41)
```

**Problem:** No cap exists. With MAX_STEPS=10 and worst-case errors, temperature could reach 2.7, exceeding API limits (typically 2.0).

#### 4. No Token Budgeting (CONFIRMED)

Location: `tinyagent/agents/react.py:355-370`

**Missing:**
- No input token counting (no `tiktoken` integration)
- No context window checks before API calls
- Pruning only occurs after tool execution (`react.py:305-306`), not before LLM calls

### Code Duplication Analysis (CRITICAL)

**Total Duplication Estimate:** ~100 lines between ReactAgent and TinyCodeAgent

#### High-Priority Duplications

| Logic | ReactAgent | TinyCodeAgent | Severity |
|-------|-----------|---------------|----------|
| RunResult for step_limit | `react.py:343-351` | `code.py:379-387` | Identical (9 lines) |
| Memory pruning check | `react.py:304-306` | `code.py:361-363` | Identical (3 lines) |
| Memory initialization | `react.py:165-170` | `code.py:249-253` | Nearly identical (6 lines) |
| Main run loop pattern | `react.py:144-163` | `code.py:222-240` | Structural (~20 lines) |
| StepLimitReached handling | `react.py:337-352` | `code.py:373-388` | Pattern (~16 lines) |
| RunResult for success | `react.py:253-264` | `code.py:340-347` | Nearly identical (~12 lines) |

#### Example: Identical RunResult for Step Limit

**ReactAgent** (`react.py:343-351`):
```python
if return_result:
    return RunResult(
        output="",
        final_answer=None,
        state="step_limit_reached",
        steps_taken=steps_taken,
        duration_seconds=duration,
        error=error,
    )
```

**TinyCodeAgent** (`code.py:379-387`):
```python
if return_result:
    return RunResult(
        output="",
        final_answer=None,
        state="step_limit_reached",
        steps_taken=steps_taken,
        duration_seconds=duration,
        error=error,
    )
```

## Key Patterns / Solutions Found

### From PLAN.md Proposed Solutions

| Pattern | Description | LOC Target |
|---------|-------------|------------|
| Extract response parsing | `_handle_llm_response()` | 15 LOC |
| Create action router | `_route_action()` for scratchpad/tool/answer | 20 LOC |
| Token-aware memory prune | Pre-LLM call pruning | 30 LOC |
| Temperature governor | Cap at 1.5, gradient scaling | 10 LOC |
| Scratchpad role migration | `assistant` role instead of `user` | 8 LOC |

### Recommended BaseAgent Abstractions

These methods should be extracted to BaseAgent:

1. `_execute_run_loop()` - Core loop infrastructure
2. `_initialize_memory()` - Clear + system prompt + task
3. `_apply_pruning()` - Conditional pruning check
4. `_create_success_result()` - RunResult factory
5. `_create_step_limit_result()` - RunResult factory
6. `_handle_step_limit_reached()` - Error handling pattern

## Knowledge Gaps

1. **Token Counting Backend:** PLAN.md asks `tiktoken` vs `transformers` - needs decision
2. **Scratchpad Role:** Should be `assistant` or `user`? Trade-off between context integrity and spec compliance
3. **Max Temperature Cap:** Proposed 1.5, needs validation against different models
4. **Pruning Strategy:** Currently `keep_last_n_steps`, may need token-aware alternatives

## Risk Assessment

| Risk | Mitigation (from PLAN.md) |
|------|---------------------------|
| Breaking changes | Feature flag for legacy+new paths |
| Step tracking | Add `step_version: 2` metadata |
| Performance regression | Log step breakdown timing |

## References

- `PLAN.md` - Original refactoring plan
- `tinyagent/agents/react.py` - ReactAgent implementation
- `tinyagent/agents/code.py` - TinyCodeAgent implementation
- `tinyagent/agents/base.py` - BaseAgent abstract class
- `tinyagent/memory/steps.py` - Step types including ScratchpadStep
- `documentation/architecture/agents/reactagent-architecture.md` - Architecture docs

## Summary

All four key issues from PLAN.md are **confirmed**:
1. `_process_step` has 7 responsibilities (cyclomatic complexity 8)
2. Scratchpads inject synthetic `user` messages, breaking role continuity
3. Temperature increments are unbounded (can exceed 2.0)
4. No token budgeting exists before API calls

Additionally, **significant code duplication** (~100 lines) exists between ReactAgent and TinyCodeAgent that violates DRY principle and should be abstracted to BaseAgent.

The refactoring plan's proposed phases are well-structured:
- **Phase 1 (Decomposition):** Extract subfunctions from `_process_step`
- **Phase 2 (State Isolation):** Introduce `AgentState` dataclass
- **Phase 3 (LLM Optimization):** Token counting and temperature governance
