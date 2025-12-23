# Research - SmolAgents-Style Memory System for tinyAgent

**Date:** 2025-12-23
**Owner:** claude-agent
**Phase:** Research
**Git Commit:** a47826b

## Goal

Research and document the implementation approach for adding a structured memory system to tinyAgent, inspired by HuggingFace SmolAgents. This replaces the current raw `list[dict[str, str]]` message accumulation with typed steps, pruning strategies, and history management.

---

## Findings

### Current tinyAgent Architecture

| File | Purpose | Relevance |
|------|---------|-----------|
| `tinyagent/agents/react.py` | JSON tool-calling ReAct agent | Lines 107-186: message accumulation |
| `tinyagent/agents/code.py` | Python code execution agent | Lines 215-308: message accumulation |
| `tinyagent/agents/base.py` | Abstract base class | Shared tool validation |
| `tinyagent/memory/scratchpad.py` | Working memory (AgentMemory) | Variables, observations, failed_approaches |
| `tinyagent/core/types.py` | FinalAnswer, RunResult | Execution metadata types |
| `tinyagent/limits/boundaries.py` | ExecutionLimits | Truncation logic at line 115-134 |

### Current Message Handling Pattern

Both agents use identical message accumulation:

```python
# tinyagent/agents/react.py:107-110
messages: list[dict[str, str]] = [
    {"role": "system", "content": self._system_prompt},
    {"role": "user", "content": question},
]

# Accumulation pattern (lines 133-186)
messages += [
    {"role": "assistant", "content": assistant_reply},
    {"role": "user", "content": f"Observation: {result}"},
]
```

**Key Issues Identified:**
1. Messages accumulate unbounded - no pruning
2. Only single-point truncation: `MAX_OBS_LEN = 500` (react.py:34)
3. No typed step structure - just raw dicts
4. No history inspection capability
5. AgentMemory lists (observations, failed_approaches) also unbounded

### SmolAgents Memory Architecture (from web research)

SmolAgents uses a clean typed step hierarchy:

| Step Type | Purpose | to_messages() Output |
|-----------|---------|---------------------|
| `MemoryStep` | Base class | Abstract |
| `SystemPromptStep` | System prompt | System message (empty in summary mode) |
| `TaskStep` | User task + images | User message |
| `ActionStep` | Thought + action + observation | 5 messages (assistant, tool call, images, tool response, error) |
| `PlanningStep` | Multi-step planning | Planning context |
| `FinalAnswerStep` | Final output | No messages (terminal) |

**Critical Finding:** SmolAgents has NO automatic pruning strategies. The `keep_last_n` and `prune_old_observations` mentioned in the spec are **proposed features, not existing ones**.

SmolAgents approach:
- Manual memory management via `agent.memory.steps`
- Callback system for custom pruning
- Community requests for pruning (issues #901, #694, #1121)

### Existing tinyAgent Truncation Patterns

| Location | Pattern | Details |
|----------|---------|---------|
| `react.py:34` | `MAX_OBS_LEN = 500` | Truncates tool observations |
| `react.py:178-181` | Observation truncation | `(result[:500] + "...")` |
| `limits/boundaries.py:115-134` | `truncate_output()` | UTF-8 byte-based, adds "[OUTPUT TRUNCATED]" |
| `observability/logger.py:42` | `content_preview_len = 200` | Display truncation only |
| `observability/logger.py:289-294` | `truncate(text, max_len)` | Generic with "..." suffix |

### Existing Test Patterns

From `tests/test_base_agent.py` and `tests/test_logger.py`:

1. **Class-based organization**: `TestComponentName` convention
2. **No fixtures**: Inline setup in each test method
3. **No mocking**: Use `api_key="test-key"` instead of mocking OpenAI
4. **Type hints**: All methods use `-> None`
5. **Contrastive testing**: Test pass/fail pairs
6. **Output capture**: `io.StringIO()` for stream testing
7. **Precise error matching**: Regex in `pytest.raises(match=...)`

---

## Key Patterns / Solutions Found

### 1. Polymorphic Step Classes (from SmolAgents)

```python
@dataclass
class Step:
    timestamp: float
    step_number: int

    def to_messages(self, summary_mode: bool = False) -> list[dict[str, str]]:
        """Each step knows how to serialize itself."""
        raise NotImplementedError

    def truncate(self, max_length: int) -> "Step":
        """Return truncated copy for pruning."""
        raise NotImplementedError
```

### 2. Memory Manager Pattern

```python
@dataclass
class MemoryManager:
    steps: list[Step] = field(default_factory=list)

    def add(self, step: Step) -> None:
        self.steps.append(step)

    def to_messages(self, summary_mode: bool = False) -> list[dict[str, str]]:
        messages = []
        for step in self.steps:
            messages.extend(step.to_messages(summary_mode))
        return messages

    def prune(self, strategy: PruneStrategy) -> None:
        self.steps = strategy(self.steps)
```

### 3. Pruning Strategy Pattern (NEW - not in SmolAgents)

```python
PruneStrategy = Callable[[list[Step]], list[Step]]

def keep_last_n_steps(n: int) -> PruneStrategy:
    def prune(steps: list[Step]) -> list[Step]:
        # Always keep SystemPromptStep and TaskStep
        critical = [s for s in steps if isinstance(s, (SystemPromptStep, TaskStep))]
        other = [s for s in steps if not isinstance(s, (SystemPromptStep, TaskStep))]
        return critical + other[-n:]
    return prune

def prune_old_observations(keep_last_n: int) -> PruneStrategy:
    def prune(steps: list[Step]) -> list[Step]:
        result = []
        action_steps = [s for s in steps if isinstance(s, ActionStep)]
        for step in steps:
            if isinstance(step, ActionStep):
                if step in action_steps[-keep_last_n:]:
                    result.append(step)
                else:
                    result.append(step.truncate_observation())
            else:
                result.append(step)
        return result
    return prune
```

### 4. Integration Point in ReactAgent

```python
# Replace lines 107-110 in react.py
memory = MemoryManager()
memory.add(SystemPromptStep(content=self._system_prompt, step_number=0))
memory.add(TaskStep(task=question, step_number=0))

# Replace messages += [...] at lines 133-136, 142-145, 183-186
memory.add(ActionStep(
    thought=thought,
    tool_name=name,
    tool_args=args,
    observation=result,
    step_number=step + 1,
))

# Get messages for LLM call
messages = memory.to_messages()
```

---

## Knowledge Gaps

1. **Token counting**: No existing token estimation in tinyAgent - needed for smart pruning
2. **Summary mode behavior**: Need to define what "summary mode" means for each step type
3. **Image handling**: TinyCodeAgent doesn't handle images, but SmolAgents does - skip for now
4. **Async step callbacks**: SmolAgents has callbacks; defer for simplicity
5. **Memory persistence**: No disk serialization planned; add later if needed

---

## Implementation Specification

### Files to Create

| File | Purpose |
|------|---------|
| `tinyagent/memory/steps.py` | Step type hierarchy (Step, SystemPromptStep, TaskStep, ActionStep, ScratchpadStep) |
| `tinyagent/memory/manager.py` | MemoryManager class + pruning strategies |
| `tests/test_memory_steps.py` | Unit tests for step types |
| `tests/test_memory_manager.py` | Unit tests for manager + pruning |
| `examples/memory_demo.py` | Usage demonstration |

### Files to Modify

| File | Changes |
|------|---------|
| `tinyagent/memory/__init__.py` | Export new classes alongside AgentMemory |
| `tinyagent/agents/react.py` | Replace message list with MemoryManager |
| `tinyagent/agents/code.py` | Use `memory_manager` (avoid name collision with existing `memory` variable) |
| `tinyagent/__init__.py` | Export MemoryManager, Step types |

### Step Type Definitions

```python
# tinyagent/memory/steps.py

@dataclass
class Step:
    timestamp: float = field(default_factory=time.time)
    step_number: int = 0

    def to_messages(self) -> list[dict[str, str]]:
        raise NotImplementedError

    def truncate(self, max_length: int = 100) -> "Step":
        return self  # Default: no truncation

@dataclass
class SystemPromptStep(Step):
    content: str = ""

    def to_messages(self) -> list[dict[str, str]]:
        return [{"role": "system", "content": self.content}]

@dataclass
class TaskStep(Step):
    task: str = ""

    def to_messages(self) -> list[dict[str, str]]:
        return [{"role": "user", "content": self.task}]

@dataclass
class ActionStep(Step):
    thought: str = ""
    tool_name: str | None = None
    tool_args: dict[str, Any] = field(default_factory=dict)
    observation: str | None = None
    error: str | None = None
    is_final: bool = False
    raw_llm_response: str = ""

    def to_messages(self) -> list[dict[str, str]]:
        messages = [{"role": "assistant", "content": self.raw_llm_response}]
        if self.error:
            messages.append({"role": "user", "content": f"Error: {self.error}"})
        elif self.observation:
            messages.append({"role": "user", "content": f"Observation: {self.observation}"})
        return messages

    def truncate(self, max_length: int = 100) -> "ActionStep":
        truncated_obs = self.observation[:max_length] + "..." if self.observation and len(self.observation) > max_length else self.observation
        return ActionStep(
            timestamp=self.timestamp,
            step_number=self.step_number,
            thought=self.thought,
            tool_name=self.tool_name,
            tool_args=self.tool_args,
            observation=truncated_obs,
            error=self.error,
            is_final=self.is_final,
            raw_llm_response=self.raw_llm_response,
        )

@dataclass
class ScratchpadStep(Step):
    content: str = ""

    def to_messages(self) -> list[dict[str, str]]:
        return [
            {"role": "assistant", "content": self.content},
            {"role": "user", "content": f"Scratchpad noted: {self.content}"},
        ]
```

### Manager Definition

```python
# tinyagent/memory/manager.py

PruneStrategy = Callable[[list[Step]], list[Step]]

@dataclass
class MemoryManager:
    steps: list[Step] = field(default_factory=list)

    def add(self, step: Step) -> None:
        self.steps.append(step)

    def to_messages(self) -> list[dict[str, str]]:
        messages = []
        for step in self.steps:
            messages.extend(step.to_messages())
        return messages

    def prune(self, strategy: PruneStrategy) -> None:
        self.steps = strategy(self.steps)

    def get_steps_by_type(self, step_type: type[Step]) -> list[Step]:
        return [s for s in self.steps if isinstance(s, step_type)]

    def clear(self) -> None:
        self.steps.clear()

    @property
    def action_count(self) -> int:
        return len(self.get_steps_by_type(ActionStep))

# Pruning strategies
def keep_last_n_steps(n: int) -> PruneStrategy:
    def prune(steps: list[Step]) -> list[Step]:
        critical = [s for s in steps if isinstance(s, (SystemPromptStep, TaskStep))]
        other = [s for s in steps if not isinstance(s, (SystemPromptStep, TaskStep))]
        return critical + other[-n:]
    return prune

def prune_old_observations(keep_last_n: int, max_length: int = 100) -> PruneStrategy:
    def prune(steps: list[Step]) -> list[Step]:
        action_steps = [s for s in steps if isinstance(s, ActionStep)]
        recent_actions = set(action_steps[-keep_last_n:])

        result = []
        for step in steps:
            if isinstance(step, ActionStep) and step not in recent_actions:
                result.append(step.truncate(max_length))
            else:
                result.append(step)
        return result
    return prune

def no_pruning() -> PruneStrategy:
    return lambda steps: steps
```

### ReactAgent Integration

```python
# tinyagent/agents/react.py - modified dataclass (lines 37-62)

@dataclass(kw_only=True)
class ReactAgent(BaseAgent):
    tools: Sequence[Tool]
    model: str = "gpt-4o-mini"
    api_key: str | None = None
    prompt_file: str | None = None
    temperature: float = 0.7
    # NEW: Memory system
    memory: MemoryManager | None = None
    enable_pruning: bool = False
    prune_keep_last: int = 5

# In __post_init__ (after line 78):
if self.memory is None:
    self.memory = MemoryManager()

# In run() - replace lines 107-110:
self.memory.clear()
self.memory.add(SystemPromptStep(content=self._system_prompt, step_number=0, timestamp=time.time()))
self.memory.add(TaskStep(task=question, step_number=0, timestamp=time.time()))

# In run() - replace line 125:
messages = self.memory.to_messages()

# In run() - replace lines 133-136, 142-145, 183-186:
self.memory.add(ActionStep(
    step_number=step + 1,
    thought="",  # Extracted from payload if present
    tool_name=name,
    tool_args=args,
    observation=short,
    error=None if ok else str(result),
    is_final=False,
    raw_llm_response=assistant_reply,
))

# Optional pruning after each step:
if self.enable_pruning:
    self.memory.prune(prune_old_observations(self.prune_keep_last))
```

---

## Backward Compatibility Notes

| Concern | Solution |
|---------|----------|
| Memory auto-initialization | Default `memory=None` triggers creation in `__post_init__` |
| Pruning off by default | `enable_pruning=False` preserves current behavior |
| Existing tests | No changes needed - they don't test message internals |
| AgentMemory (scratchpad) | Renamed to `memory_manager` in TinyCodeAgent to avoid collision |

---

## Implementation Order

1. **Core memory module**
   - Create `tinyagent/memory/steps.py` with all step types
   - Create `tinyagent/memory/manager.py` with MemoryManager + pruning
   - Update `tinyagent/memory/__init__.py` exports
   - Write `tests/test_memory_steps.py` and `tests/test_memory_manager.py`

2. **ReactAgent integration**
   - Add memory parameters to dataclass
   - Modify `run()` to use MemoryManager
   - Ensure backward compatibility

3. **TinyCodeAgent integration**
   - Add `memory_manager` parameter (avoid name collision)
   - Integrate with existing AgentMemory scratchpad

4. **Documentation and examples**
   - Create `examples/memory_demo.py`
   - Update module docstrings

---

## References

### Codebase Files
- `tinyagent/agents/react.py:107-186` - Current message handling
- `tinyagent/agents/code.py:215-308` - Code agent message handling
- `tinyagent/memory/scratchpad.py:19-159` - Existing AgentMemory
- `tinyagent/limits/boundaries.py:115-134` - Truncation pattern
- `tests/test_base_agent.py` - Test patterns
- `tests/test_logger.py` - Output testing patterns

### External Sources
- [SmolAgents memory.py](https://github.com/huggingface/smolagents/blob/v1.21.0/src/smolagents/memory.py)
- [SmolAgents agents.py](https://github.com/huggingface/smolagents/blob/main/src/smolagents/agents.py)
- [Memory management tutorial](https://huggingface.co/docs/smolagents/en/tutorials/memory)
- [Memory consolidation request #901](https://github.com/huggingface/smolagents/issues/901)
- [Memory bank proposal #1121](https://github.com/huggingface/smolagents/issues/1121)
