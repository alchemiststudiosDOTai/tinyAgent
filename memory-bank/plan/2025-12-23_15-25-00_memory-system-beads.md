---
title: "SmolAgents-Style Memory System - Beads Plan"
phase: Plan
date: "2025-12-23T15:25:00"
owner: "claude-agent"
parent_research: "memory-bank/research/2025-12-23_14-12-31_smolagents-memory-system.md"
git_commit_at_plan: "a47826b"
beads_count: 9
tags: [plan, beads, memory, coding]
---

## Goal

- Implement a structured memory system with typed Step classes and pruning strategies for tinyAgent.
- Non-goals: Token counting, image handling, async callbacks, disk persistence.

## Scope & Assumptions

### In Scope
- Step type hierarchy (Step, SystemPromptStep, TaskStep, ActionStep, ScratchpadStep)
- MemoryManager class with step storage and message serialization
- Pruning strategies (keep_last_n_steps, prune_old_observations, no_pruning)
- ReactAgent integration with backward compatibility
- TinyCodeAgent integration (memory_manager to avoid naming collision)
- Unit tests for all new components
- Demo example

### Out of Scope
- Token estimation/counting
- Summary mode variations
- Image handling (SmolAgents feature not needed here)
- Async step callbacks
- Memory persistence to disk

### Assumptions
- Python 3.10+ dataclass patterns
- Existing test patterns from tests/test_base_agent.py
- OpenRouter compatibility via "user" role for tool responses

## Deliverables

- `tinyagent/memory/steps.py` - Step type hierarchy
- `tinyagent/memory/manager.py` - MemoryManager + pruning strategies
- `tinyagent/memory/__init__.py` - Updated exports
- `tinyagent/__init__.py` - Main package exports
- `tinyagent/agents/react.py` - Memory integration
- `tinyagent/agents/code.py` - Memory integration
- `tests/test_memory_steps.py` - Step type tests
- `tests/test_memory_manager.py` - Manager tests
- `examples/memory_demo.py` - Usage demonstration

## Readiness

- [x] Research document completed
- [x] Git state verified (a47826b)
- [x] Existing code patterns analyzed
- [x] Test patterns documented
- [x] Beads created with dependencies

## Beads Overview

| ID | Title | Priority | Dependencies | Tags |
|----|-------|----------|--------------|------|
| tinyAgent-bbe | Create Step type hierarchy | P0 | - | core, setup |
| tinyAgent-tv0 | Create MemoryManager and pruning | P0 | tinyAgent-bbe | core, setup |
| tinyAgent-xys | Write unit tests for Step types | P1 | tinyAgent-bbe | test |
| tinyAgent-fgd | Write unit tests for MemoryManager | P1 | tinyAgent-tv0 | test |
| tinyAgent-4sk | Update memory __init__.py exports | P1 | tinyAgent-tv0 | core |
| tinyAgent-8sm | Integrate MemoryManager into ReactAgent | P1 | tinyAgent-4sk, tinyAgent-fgd | core |
| tinyAgent-dw0 | Integrate MemoryManager into TinyCodeAgent | P1 | tinyAgent-8sm | core |
| tinyAgent-hty | Update main package exports | P2 | tinyAgent-4sk | core |
| tinyAgent-9hv | Create memory demo example | P2 | tinyAgent-8sm | docs |

## Dependency Graph

```
tinyAgent-bbe (P0) [READY]
    |
    +---> tinyAgent-tv0 (P0)
    |         |
    |         +---> tinyAgent-4sk (P1)
    |         |         |
    |         |         +---> tinyAgent-8sm (P1)
    |         |         |         |
    |         |         |         +---> tinyAgent-dw0 (P1)
    |         |         |         |
    |         |         |         +---> tinyAgent-9hv (P2)
    |         |         |
    |         |         +---> tinyAgent-hty (P2)
    |         |
    |         +---> tinyAgent-fgd (P1)
    |                   |
    |                   +---> tinyAgent-8sm (P1) [joins above]
    |
    +---> tinyAgent-xys (P1)
```

## Bead Details

### tinyAgent-bbe: Create Step type hierarchy in tinyagent/memory/steps.py
**Priority:** P0
**Dependencies:** None
**Tags:** core, setup

#### Summary
Create the core Step dataclass hierarchy with polymorphic to_messages() methods.

#### Acceptance Criteria
- [ ] Base Step dataclass with timestamp and step_number fields
- [ ] SystemPromptStep with content field, returns system message
- [ ] TaskStep with task field, returns user message
- [ ] ActionStep with thought, tool_name, tool_args, observation, error, is_final, raw_llm_response
- [ ] ActionStep.truncate() method for observation truncation
- [ ] ScratchpadStep for working memory notes
- [ ] All step types have to_messages() returning list[dict[str, str]]

#### Files
- tinyagent/memory/steps.py (create)

#### Notes
- Use @dataclass decorator with field(default_factory=...) patterns
- Follow existing type hint patterns from codebase
- Import time for timestamp defaults

---

### tinyAgent-tv0: Create MemoryManager and pruning strategies
**Priority:** P0
**Dependencies:** tinyAgent-bbe
**Tags:** core, setup

#### Summary
Create the MemoryManager class that stores steps and provides pruning strategies.

#### Acceptance Criteria
- [ ] MemoryManager dataclass with steps: list[Step]
- [ ] add(step: Step) method to append steps
- [ ] to_messages() method aggregating all step messages
- [ ] prune(strategy: PruneStrategy) method to apply pruning
- [ ] get_steps_by_type(step_type) method for filtering
- [ ] clear() method to reset steps
- [ ] action_count property for counting ActionSteps
- [ ] PruneStrategy type alias: Callable[[list[Step]], list[Step]]
- [ ] keep_last_n_steps(n) strategy preserving SystemPromptStep and TaskStep
- [ ] prune_old_observations(keep_last_n, max_length) strategy
- [ ] no_pruning() strategy (identity function)

#### Files
- tinyagent/memory/manager.py (create)

#### Notes
- Import Step types from steps.py
- Use isinstance checks for type filtering
- Pruning strategies are factory functions returning callables

---

### tinyAgent-xys: Write unit tests for Step types
**Priority:** P1
**Dependencies:** tinyAgent-bbe
**Tags:** test

#### Summary
Create comprehensive unit tests for all Step type classes.

#### Acceptance Criteria
- [ ] TestStep class testing base Step initialization and defaults
- [ ] TestSystemPromptStep testing to_messages() output format
- [ ] TestTaskStep testing to_messages() output format
- [ ] TestActionStep testing to_messages() with observation vs error cases
- [ ] TestActionStep testing truncate() method behavior
- [ ] TestScratchpadStep testing to_messages() dual message output
- [ ] Contrastive tests: valid vs invalid step configurations
- [ ] All tests use -> None type hints

#### Files
- tests/test_memory_steps.py (create)

#### Notes
- Follow patterns from tests/test_base_agent.py
- No mocking required - direct instantiation
- Use pytest.raises for error cases

---

### tinyAgent-fgd: Write unit tests for MemoryManager
**Priority:** P1
**Dependencies:** tinyAgent-tv0
**Tags:** test

#### Summary
Create comprehensive unit tests for MemoryManager and pruning strategies.

#### Acceptance Criteria
- [ ] TestMemoryManager testing add(), to_messages(), clear()
- [ ] TestMemoryManager testing get_steps_by_type() filtering
- [ ] TestMemoryManager testing action_count property
- [ ] TestKeepLastNSteps testing critical step preservation
- [ ] TestPruneOldObservations testing observation truncation for old steps
- [ ] TestNoPruning testing identity behavior
- [ ] Contrastive tests: pruned vs unpruned state comparisons
- [ ] Integration test: full workflow with multiple step types

#### Files
- tests/test_memory_manager.py (create)

#### Notes
- Follow patterns from tests/test_base_agent.py
- Create test fixtures with multiple step types
- Verify step ordering after pruning

---

### tinyAgent-4sk: Update tinyagent/memory/__init__.py exports
**Priority:** P1
**Dependencies:** tinyAgent-tv0
**Tags:** core

#### Summary
Update the memory module exports to include new Step types and MemoryManager.

#### Acceptance Criteria
- [ ] Export Step, SystemPromptStep, TaskStep, ActionStep, ScratchpadStep from steps
- [ ] Export MemoryManager from manager
- [ ] Export pruning strategies: keep_last_n_steps, prune_old_observations, no_pruning
- [ ] Export PruneStrategy type alias
- [ ] Maintain existing AgentMemory export for backward compatibility
- [ ] Update __all__ list with all exports

#### Files
- tinyagent/memory/__init__.py (modify)

#### Notes
- Check existing exports first to avoid breaking changes
- Use explicit imports rather than star imports

---

### tinyAgent-8sm: Integrate MemoryManager into ReactAgent
**Priority:** P1
**Dependencies:** tinyAgent-4sk, tinyAgent-fgd
**Tags:** core

#### Summary
Replace the raw message list in ReactAgent with MemoryManager.

#### Acceptance Criteria
- [ ] Add memory: MemoryManager | None = None parameter to ReactAgent dataclass
- [ ] Add enable_pruning: bool = False parameter
- [ ] Add prune_keep_last: int = 5 parameter
- [ ] Auto-initialize memory in __post_init__ if None
- [ ] Replace messages list initialization with memory.clear() + memory.add(SystemPromptStep, TaskStep)
- [ ] Replace messages += [...] with memory.add(ActionStep(...))
- [ ] Replace messages variable with memory.to_messages() for LLM calls
- [ ] Apply pruning after each step when enable_pruning=True
- [ ] Backward compatible: existing code without memory param works unchanged

#### Files
- tinyagent/agents/react.py (modify lines 37-62, 107-186)

#### Notes
- Import time for step timestamps
- Import MemoryManager, Step types from tinyagent.memory
- Preserve existing MAX_OBS_LEN truncation behavior in ActionStep

---

### tinyAgent-dw0: Integrate MemoryManager into TinyCodeAgent
**Priority:** P1
**Dependencies:** tinyAgent-8sm
**Tags:** core

#### Summary
Add MemoryManager to TinyCodeAgent using memory_manager attribute name.

#### Acceptance Criteria
- [ ] Add memory_manager: MemoryManager | None = None parameter
- [ ] Add enable_pruning: bool = False parameter
- [ ] Add prune_keep_last: int = 5 parameter
- [ ] Auto-initialize memory_manager in __post_init__ if None
- [ ] Replace messages list with memory_manager step operations
- [ ] Existing memory (AgentMemory scratchpad) remains unchanged
- [ ] Apply pruning when enabled
- [ ] Backward compatible: existing code works unchanged

#### Files
- tinyagent/agents/code.py (modify lines 30-70, 215-308)

#### Notes
- Use memory_manager to avoid naming collision with existing memory attribute
- The existing memory (AgentMemory) serves different purpose (scratchpad)
- Follow same pattern as ReactAgent integration

---

### tinyAgent-hty: Update main tinyagent/__init__.py exports
**Priority:** P2
**Dependencies:** tinyAgent-4sk
**Tags:** core

#### Summary
Export MemoryManager and Step types from the main tinyagent package.

#### Acceptance Criteria
- [ ] Export MemoryManager from tinyagent.memory
- [ ] Export Step, SystemPromptStep, TaskStep, ActionStep, ScratchpadStep
- [ ] Export PruneStrategy type alias
- [ ] Export pruning strategy functions
- [ ] Update __all__ list
- [ ] Verify imports work: from tinyagent import MemoryManager, ActionStep

#### Files
- tinyagent/__init__.py (modify)

#### Notes
- Add to existing exports, don't replace
- Keep import structure clean

---

### tinyAgent-9hv: Create memory system demo example
**Priority:** P2
**Dependencies:** tinyAgent-8sm
**Tags:** docs

#### Summary
Create a demonstration script showing memory system usage.

#### Acceptance Criteria
- [ ] Create examples/memory_demo.py
- [ ] Demo 1: Basic memory usage without pruning
- [ ] Demo 2: Memory with keep_last_n_steps pruning
- [ ] Demo 3: Memory with prune_old_observations strategy
- [ ] Show step inspection via get_steps_by_type()
- [ ] Display action_count property usage
- [ ] Include comments explaining each feature
- [ ] Script runs without errors

#### Files
- examples/memory_demo.py (create)

#### Notes
- Follow patterns from examples/simple_demo.py
- Use real tool calls to generate ActionSteps
- Print memory state before and after pruning

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing ReactAgent tests | Memory auto-initialized, pruning off by default |
| Naming collision in TinyCodeAgent | Use memory_manager instead of memory |
| Message format compatibility | Preserve "user" role for OpenRouter compatibility |
| Step type proliferation | Start minimal, add types only as needed |

## Test Strategy

- `tests/test_memory_steps.py`: Unit tests for each Step type
- `tests/test_memory_manager.py`: Unit tests for MemoryManager and pruning
- Existing `tests/test_agent.py`: Verify backward compatibility (no changes needed)
- `examples/memory_demo.py`: Integration demonstration

## References

### Research Document
- `memory-bank/research/2025-12-23_14-12-31_smolagents-memory-system.md`

### Key Code Refs
- `tinyagent/agents/react.py:107-186` - Current message handling
- `tinyagent/agents/code.py:215-308` - Code agent messages
- `tinyagent/memory/scratchpad.py:19-159` - Existing AgentMemory
- `tests/test_base_agent.py` - Test patterns

### External Sources
- [SmolAgents memory.py](https://github.com/huggingface/smolagents/blob/v1.21.0/src/smolagents/memory.py)

## Ready Queue

```
tinyAgent-bbe (P0) - Create Step type hierarchy [READY - no dependencies]
```

After tinyAgent-bbe completes:
```
tinyAgent-tv0 (P0) - Create MemoryManager
tinyAgent-xys (P1) - Write unit tests for Step types
```

## Final Gate

- Plan path: `memory-bank/plan/2025-12-23_15-25-00_memory-system-beads.md`
- Beads created: 9
- Ready for execution: 1 (tinyAgent-bbe)
- Blocked: 8
- Dependency cycles: None
- Next command: `/context-engineer:execute-beads`
