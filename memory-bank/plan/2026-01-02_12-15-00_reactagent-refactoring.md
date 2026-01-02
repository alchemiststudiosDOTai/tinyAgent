---
title: "ReactAgent Refactoring - Plan"
phase: Plan
date: "2026-01-02T12:15:00"
owner: "Agent"
parent_research: "memory-bank/research/2026-01-02_11-25-00_reactagent-refactoring-analysis.md"
git_commit_at_plan: "9b8d716"
tags: [plan, reactagent, refactoring, coding]
---

## Goal

- **Singular outcome:** Reduce `_process_step` cyclomatic complexity from 8 to 3 by extracting responsibilities into composable subfunctions, and eliminate ~100 lines of code duplication between ReactAgent and TinyCodeAgent by abstracting shared logic to BaseAgent.

### Non-Goals

- No deployment/CI changes
- No new external dependencies (no tiktoken in this phase)
- No feature flags or backwards-compatibility shims
- No observability/metrics infrastructure

## Scope & Assumptions

### In Scope

1. Extract subfunctions from `_process_step` in ReactAgent
2. Add temperature cap (1.5) to prevent API limit violations
3. Fix ScratchpadStep role continuity issue
4. Abstract duplicated RunResult factory methods to BaseAgent
5. Abstract duplicated memory initialization to BaseAgent
6. Abstract duplicated pruning logic to BaseAgent

### Out of Scope

- Token counting/budgeting (deferred to future phase)
- `AgentState` dataclass introduction (deferred - not needed for decomposition)
- Container/sandbox executor implementations

### Assumptions

- OpenAI API temperature cap is 2.0; we use 1.5 for safety margin
- Scratchpad role can be changed to `assistant` without breaking existing behavior
- Tests exist in `tests/` that can validate changes

## Deliverables

| Deliverable | Target File |
|-------------|-------------|
| Temperature governor constant | `tinyagent/agents/react.py` |
| Extracted `_handle_llm_response()` | `tinyagent/agents/react.py` |
| Extracted `_route_action()` | `tinyagent/agents/react.py` |
| Fixed ScratchpadStep role | `tinyagent/memory/steps.py` |
| BaseAgent._create_success_result() | `tinyagent/agents/base.py` |
| BaseAgent._create_step_limit_result() | `tinyagent/agents/base.py` |
| BaseAgent._initialize_memory() | `tinyagent/agents/base.py` |
| BaseAgent._apply_pruning() | `tinyagent/agents/base.py` |

## Readiness

### Preconditions

- [x] Research document validated findings
- [x] Git repo on `tooling` branch at commit `9b8d716`
- [x] Existing files readable and understood
- [ ] Tests passing before changes (verify with `uv run pytest`)

### Required Context

- `tinyagent/agents/react.py` - ReactAgent implementation
- `tinyagent/agents/code.py` - TinyCodeAgent (for duplication reference)
- `tinyagent/agents/base.py` - BaseAgent abstract class
- `tinyagent/memory/steps.py` - ScratchpadStep class
- `tinyagent/core/types.py` - RunResult dataclass

## Milestones

### M1: Temperature Governance
Add temperature cap to prevent API violations.

### M2: ScratchpadStep Role Fix
Change synthetic `user` messages to proper role handling.

### M3: Process Step Decomposition
Extract subfunctions from `_process_step` to reduce complexity.

### M4: BaseAgent Abstractions
Centralize duplicated logic from ReactAgent and TinyCodeAgent.

## Work Breakdown (Tasks)

### M1 Tasks

| ID | Task | Files | Dependencies | Acceptance Test |
|----|------|-------|--------------|-----------------|
| T1.1 | Add `MAX_TEMPERATURE` constant (1.5) to react.py | `react.py:41` | None | Constant exists with value 1.5 |
| T1.2 | Cap temperature increment in run loop | `react.py:159-160` | T1.1 | Temperature never exceeds MAX_TEMPERATURE |

### M2 Tasks

| ID | Task | Files | Dependencies | Acceptance Test |
|----|------|-------|--------------|-----------------|
| T2.1 | Change ScratchpadStep.to_messages() to omit synthetic user message | `steps.py:171-184` | None | Only assistant message returned when raw_llm_response present |

### M3 Tasks

| ID | Task | Files | Dependencies | Acceptance Test |
|----|------|-------|--------------|-----------------|
| T3.1 | Extract `_handle_llm_response()` - parse + validate | `react.py` | None | Method exists, returns `(payload, error_str)` tuple |
| T3.2 | Extract `_route_action()` - dispatch scratchpad/tool/answer | `react.py` | T3.1 | Method exists, returns `(result, increment_temp)` |
| T3.3 | Refactor `_process_step()` to use extracted methods | `react.py:172-224` | T3.1, T3.2 | Cyclomatic complexity <= 3 |

### M4 Tasks

| ID | Task | Files | Dependencies | Acceptance Test |
|----|------|-------|--------------|-----------------|
| T4.1 | Add `_create_step_limit_result()` to BaseAgent | `base.py` | None | Method returns RunResult with state="step_limit_reached" |
| T4.2 | Add `_create_success_result()` to BaseAgent | `base.py` | None | Method returns RunResult with state="completed" |
| T4.3 | Add `_initialize_memory()` to BaseAgent | `base.py` | None | Method clears + adds system prompt + task |
| T4.4 | Add `_apply_pruning()` to BaseAgent | `base.py` | None | Method applies pruning strategy to memory |
| T4.5 | Refactor ReactAgent to use BaseAgent methods | `react.py` | T4.1-T4.4 | No inline RunResult construction |
| T4.6 | Refactor TinyCodeAgent to use BaseAgent methods | `code.py` | T4.1-T4.4 | No inline RunResult construction |

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | Medium | High | Run tests after each task completion |
| Role change affects LLM behavior | Low | Medium | Test with sample prompts before/after |
| BaseAgent changes break subclasses | Medium | High | Run both agent types through tests |

## Test Strategy

- Run `uv run pytest` after each milestone
- Focus on existing test coverage, not adding new tests
- Manual verification for scratchpad role change (test one prompt before/after)

## References

- Research doc: `memory-bank/research/2026-01-02_11-25-00_reactagent-refactoring-analysis.md`
- PLAN.md: Original refactoring plan
- ReactAgent: `tinyagent/agents/react.py:51-392`
- TinyCodeAgent: `tinyagent/agents/code.py:67-421`
- BaseAgent: `tinyagent/agents/base.py:28-112`
- ScratchpadStep: `tinyagent/memory/steps.py:155-185`

## Final Gate

| Check | Status |
|-------|--------|
| Plan path | `memory-bank/plan/2026-01-02_12-15-00_reactagent-refactoring.md` |
| Milestone count | 4 |
| Task count | 12 |
| All tasks have acceptance tests | Yes |
| All tasks have file targets | Yes |

**Next command:** `/ce:ex memory-bank/plan/2026-01-02_12-15-00_reactagent-refactoring.md`
