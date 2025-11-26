# PRD: TinyCodeAgent v2

**Date:** 2025-11-25
**Status:** Draft
**Owner:** tuna

---

## Vision

A code agent that behaves like a junior developer with infinite patience and zero ego. It thinks in code, fails cheaply, and knows when it's done.

---

## Core Principles

### 1. Junior Dev Mindset
- Understands intent, not just instructions
- When something breaks, tries another approach
- Honest about uncertainty - explores before committing
- Verifies outcomes match intent

### 2. Tools as Extensions, Not Forms
- Code-first interaction (not JSON tool calling)
- Tools feel like natural Python functions
- Minimal ceremony between thought and action

### 3. Failure is Cheap
- Every execution is potentially hostile
- Timeouts on everything
- Resource caps enforced
- Killable at any moment
- Never blocks, never hangs

### 4. Boundaries Don't Exist (Because They Can't)
- Dangerous operations aren't "blocked" - they don't exist
- No checking, no validation at runtime
- The unsafe world is simply unreachable

### 5. Boring and Predictable
- Same input → same output
- Creative in problem-solving, robotic in execution
- No surprises

---

## Functional Requirements

### FR1: Graduated Trust Model

| Trust Level | Execution Environment | Use Case |
|-------------|----------------------|----------|
| `local` | Restricted exec() (current) | Trusted tools, fast iteration |
| `isolated` | Subprocess with timeout | Default for most use |
| `sandboxed` | Container/VM | Untrusted inputs, production |

```python
agent = TinyCodeAgent(
    tools=[...],
    trust_level="isolated",  # NEW
)
```

### FR2: Working Memory (Scratchpad)

Agent maintains state across steps:

```python
@dataclass
class AgentMemory:
    variables: dict[str, Any]      # Computed values
    observations: list[str]        # What it learned
    failed_approaches: list[str]   # What didn't work
```

Injected into each code execution. LLM can read/write.

### FR3: Execution Boundaries

| Resource | Limit | Behavior on Exceed |
|----------|-------|-------------------|
| Time | 30s default, configurable | Kill + report timeout |
| Memory | 256MB default | Kill + report OOM |
| Output | 10KB | Truncate + warn |
| Steps | 10 default | Stop + return partial |

```python
agent = TinyCodeAgent(
    tools=[...],
    limits=ExecutionLimits(
        timeout_seconds=30,
        max_memory_mb=256,
        max_output_bytes=10_000,
        max_steps=10,
    ),
)
```

### FR4: Completion Verification

Agent doesn't just call `final_answer()`. It verifies:

```python
# OLD: Just signal completion
final_answer(result)

# NEW: Signal with verification
final_answer(
    result,
    verified_by="checked output contains expected format",  # Optional rationale
)
```

Agent can also be configured to auto-verify:

```python
agent = TinyCodeAgent(
    tools=[...],
    verify_completion=True,  # Adds verification step before returning
)
```

### FR5: Honest Uncertainty

LLM can signal confidence:

```python
# Available in exec namespace
uncertain("I'm not sure if this API returns a list or dict")
explore("Let me check the structure first")
commit("Now I know the format, proceeding with solution")
```

These become observations in the scratchpad, visible to the orchestrator.

---

## Non-Functional Requirements

### NFR1: Performance
- Local trust level: <50ms overhead per step
- Isolated trust level: <200ms overhead per step
- Cold start: <1s

### NFR2: Reliability
- No execution can hang the agent
- All failures recoverable
- Deterministic given same inputs + same model

### NFR3: Observability
- Every step logged with: code, output, duration, memory used
- Structured logs (JSON) for programmatic access
- Optional verbose mode for debugging

### NFR4: Simplicity
- Core implementation <500 lines
- Zero required dependencies beyond openai
- Optional dependencies for isolation (docker, etc.)

---

## Technical Design

### Executor Abstraction

```python
class Executor(Protocol):
    def run(self, code: str, namespace: dict) -> ExecutionResult: ...
    def kill(self) -> None: ...

@dataclass
class ExecutionResult:
    output: str
    is_final: bool
    duration_ms: int
    memory_used_bytes: int
    error: str | None = None
    timeout: bool = False
```

### Implementations

1. **LocalExecutor** - Current impl, restricted exec()
2. **SubprocessExecutor** - Fork + exec with resource limits
3. **DockerExecutor** - Container-based (optional)

### Agent Loop (Revised)

```
1. Initialize memory (scratchpad)
2. FOR step in range(max_steps):
   a. Build context: system prompt + memory + task + history
   b. Get LLM response
   c. Extract code block
   d. Execute with timeout:
      - Inject tools + memory into namespace
      - Run via selected executor
      - Capture result OR timeout/error
   e. Update memory with observations
   f. If final_answer called:
      - Optional: verify completion
      - Return result
   g. If error/timeout:
      - Add to failed_approaches
      - Continue (let LLM retry)
3. Return partial result or raise StepLimitReached
```

---

## Migration Path

### Phase 1: Boundaries
- Add timeout wrapper to current executor
- Add output truncation
- Add memory tracking (reporting only)

### Phase 2: Executor Abstraction
- Extract Executor protocol
- Implement SubprocessExecutor
- Make executor configurable

### Phase 3: Working Memory
- Implement AgentMemory
- Inject into namespace
- Update system prompt to use it

### Phase 4: Polish
- Completion verification
- Uncertainty signals
- Structured logging
- Documentation

---

## Success Criteria

1. **No hangs**: Any code execution terminates within timeout
2. **Predictable**: Same task + same model = same result (within model variance)
3. **Observable**: Can reconstruct exactly what happened from logs
4. **Simple**: New contributor understands architecture in <30 min
5. **Fast**: <200ms overhead for typical step (isolated mode)

---

## Open Questions

1. **Async tools in code execution** - Worth solving or accept the limitation?
2. **State persistence** - Should memory survive across separate `run()` calls?
3. **Multi-agent** - Should agents be able to spawn sub-agents?
4. **Streaming** - Should execution stream output in real-time?

---

## References

- [Research: Code Agent Architecture](../research/2025-11-25_23-15-00_code-agent-architecture.md)
- [Comparison: tinyagent vs smolagents](../../documentation/python_execution_comparison.md)


The New World
tinyagent/
├── __init__.py                 # Public API: TinyCodeAgent, ReactAgent
│
├── agents/
│   ├── __init__.py
│   ├── react.py                # ReactAgent (unchanged)
│   └── code.py                 # TinyCodeAgent - just orchestration (~200 lines)
│
├── execution/                  # NEW - the execution layer
│   ├── __init__.py             # Exports: Executor, ExecutionResult
│   ├── protocol.py             # Executor protocol + ExecutionResult (~50 lines)
│   ├── local.py                # LocalExecutor - current restricted exec (~100 lines)
│   ├── isolated.py             # SubprocessExecutor - fork with limits (~150 lines)
│   └── sandbox.py              # DockerExecutor - optional (~100 lines)
│
├── memory/                     # NEW - working memory
│   ├── __init__.py
│   └── scratchpad.py           # AgentMemory, observations, failed_approaches (~80 lines)
│
├── signals/                    # NEW - LLM communication primitives
│   ├── __init__.py
│   └── primitives.py           # final_answer, uncertain, explore, commit (~60 lines)
│
├── limits/                     # NEW - resource boundaries
│   ├── __init__.py
│   └── boundaries.py           # ExecutionLimits, timeout wrapper (~80 lines)
│
└── tools.py                    # @tool decorator (unchanged)
