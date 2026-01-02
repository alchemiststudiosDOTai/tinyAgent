---
title: "Tool Calling Migration - Plan"
phase: Plan
date: "2026-01-01 23:15:00"
owner: "Claude Code"
parent_research: "memory-bank/research/2026-01-01_22-34-08_tool_calling_migration_research.md"
git_commit_at_plan: "d59ed1e"
tags: [plan, tool-calling, pydantic, structured-outputs, coding]
---

## Goal

- Implement a hybrid tool-calling adapter system that automatically selects the best approach (OpenAI Structured Outputs, Pydantic validation + retry, or current JSON parsing) based on the model being used.

### Non-goals

- Deployment/observability infrastructure
- Performance benchmarking across approaches
- Outlines/constrained decoding integration (Phase 3 in research - deferred)
- Streaming support for structured outputs

## Scope & Assumptions

### In Scope

- Add Pydantic-based Tool model with JSON Schema generation
- Implement adapter protocol for tool calling strategies
- Add OpenAI Structured Outputs adapter for gpt-4o+ models
- Add Validated adapter with Pydantic + retry for other models
- Integrate adapters into ReactAgent with automatic selection
- Maintain backward compatibility with current JSON parsing fallback

### Out of Scope

- Outlines library integration (requires optional dependency)
- Local model constrained decoding
- Cost analysis tooling
- Model compatibility matrix maintenance

### Assumptions

- Pydantic v2 is acceptable as a core dependency (already compatible with openai>=1.0)
- OpenAI Structured Outputs API (`response_format=json_schema`) is stable
- Current Tool dataclass can be migrated to Pydantic without breaking changes
- ReactAgent clients don't directly access Tool internals

## Deliverables

1. `tinyagent/core/schema.py` - JSON Schema conversion utilities
2. `tinyagent/core/adapters.py` - Adapter protocol and implementations
3. Updated `tinyagent/core/registry.py` - Pydantic-based Tool model
4. Updated `tinyagent/agents/react.py` - Adapter integration
5. Updated `pyproject.toml` - Pydantic dependency

## Readiness

### Preconditions

- [x] Research document complete
- [x] Current codebase reviewed (parsing.py, registry.py, react.py)
- [x] Git state clean on master (d59ed1e)
- [x] Pydantic v2 compatible with Python 3.10+

### Required Files

| File | Current State | Action |
|------|---------------|--------|
| `tinyagent/core/registry.py` | dataclass Tool | Migrate to Pydantic |
| `tinyagent/core/parsing.py` | JSON parsing utils | No change |
| `tinyagent/agents/react.py` | parse_json_response | Add adapter calls |
| `tinyagent/core/schema.py` | Does not exist | Create |
| `tinyagent/core/adapters.py` | Does not exist | Create |

## Milestones

### M1: Schema & Adapter Foundation

Create the schema conversion utilities and adapter protocol.

### M2: Pydantic Tool Model

Convert Tool dataclass to Pydantic with JSON Schema generation.

### M3: OpenAI Structured Outputs Adapter

Implement adapter for gpt-4o+ using `response_format=json_schema`.

### M4: Validated Adapter + Integration

Implement Pydantic validation with retry, integrate into ReactAgent.

## Work Breakdown (Tasks)

### M1: Schema & Adapter Foundation

#### T1.1: Create JSON Schema conversion module

**Summary:** Create `tinyagent/core/schema.py` with Python type to JSON Schema mapping.

**Owner:** Developer
**Estimate:** Small
**Dependencies:** None
**Milestone:** M1

**Files/modules:**
- `tinyagent/core/schema.py` (new)

**Implementation:**
```python
# Key functions:
def python_type_to_json_schema(python_type: type) -> dict:
    """Map Python types (str, int, list, etc.) to JSON Schema types."""

def tool_to_json_schema(tool: Tool) -> dict:
    """Convert Tool signature to JSON Schema format."""
```

**Acceptance test:**
- Unit test: `test_python_type_to_json_schema()` validates str->string, int->integer, etc.

---

#### T1.2: Create adapter protocol

**Summary:** Define `ToolCallingAdapter` protocol and `ToolCallingMode` enum in `tinyagent/core/adapters.py`.

**Owner:** Developer
**Estimate:** Small
**Dependencies:** None
**Milestone:** M1

**Files/modules:**
- `tinyagent/core/adapters.py` (new)

**Implementation:**
```python
class ToolCallingMode(Enum):
    AUTO = "auto"
    STRUCTURED = "structured"
    VALIDATED = "validated"
    PARSED = "parsed"

class ToolCallingAdapter(Protocol):
    def format_request(self, tools: list[Tool], messages: list[dict]) -> dict:
        """Return kwargs to add to chat completion request."""

    def extract_tool_call(self, response: str) -> dict | None:
        """Extract tool call from response content."""
```

**Acceptance test:**
- Unit test: Verify protocol can be implemented by stub class.

---

### M2: Pydantic Tool Model

#### T2.1: Migrate Tool to Pydantic BaseModel

**Summary:** Convert `Tool` from dataclass to Pydantic BaseModel, add `json_schema` property.

**Owner:** Developer
**Estimate:** Medium
**Dependencies:** T1.1
**Milestone:** M2

**Files/modules:**
- `tinyagent/core/registry.py` (modify)

**Implementation:**
```python
from pydantic import BaseModel, Field

class Tool(BaseModel):
    fn: Callable[..., Any] = Field(exclude=True)
    name: str
    doc: str
    signature: inspect.Signature = Field(exclude=True)
    is_async: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def json_schema(self) -> dict:
        """Generate JSON Schema for this tool's arguments."""
        return tool_to_json_schema(self)
```

**Acceptance test:**
- Existing `test_tool_decorator.py` tests pass unchanged.

---

#### T2.2: Update tool decorator for Pydantic model

**Summary:** Ensure `@tool` decorator returns Pydantic-based Tool, maintain same API.

**Owner:** Developer
**Estimate:** Small
**Dependencies:** T2.1
**Milestone:** M2

**Files/modules:**
- `tinyagent/core/registry.py` (modify)

**Implementation:**
- Change `Tool(...)` instantiation to use Pydantic model
- Keep validation logic unchanged

**Acceptance test:**
- `uv run pytest tests/test_registry.py` passes.

---

### M3: OpenAI Structured Outputs Adapter

#### T3.1: Implement OpenAIStructuredAdapter

**Summary:** Create adapter that uses `response_format=json_schema` for gpt-4o+ models.

**Owner:** Developer
**Estimate:** Medium
**Dependencies:** T1.2, T2.1
**Milestone:** M3

**Files/modules:**
- `tinyagent/core/adapters.py` (modify)

**Implementation:**
```python
class OpenAIStructuredAdapter:
    def format_request(self, tools: list[Tool], messages: list[dict]) -> dict:
        schema = self._build_combined_schema(tools)
        return {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_response",
                    "strict": True,
                    "schema": schema
                }
            }
        }

    def extract_tool_call(self, response: str) -> dict | None:
        # Direct JSON parse - no wrappers expected with structured outputs
        return json.loads(response)
```

**Acceptance test:**
- Unit test: `format_request()` produces valid OpenAI response_format structure.

---

#### T3.2: Build combined schema for tools + answer

**Summary:** Create schema that allows either tool call OR final answer response.

**Owner:** Developer
**Estimate:** Small
**Dependencies:** T3.1
**Milestone:** M3

**Files/modules:**
- `tinyagent/core/adapters.py` (modify)

**Implementation:**
```python
def _build_combined_schema(self, tools: list[Tool]) -> dict:
    """Build oneOf schema: tool_call | answer | scratchpad."""
    return {
        "type": "object",
        "properties": {
            "tool": {"type": "string", "enum": [t.name for t in tools]},
            "arguments": {"type": "object"},
            "answer": {"type": "string"},
            "scratchpad": {"type": "string"}
        },
        "additionalProperties": False
    }
```

**Acceptance test:**
- Unit test: Schema validates sample tool call and answer payloads.

---

### M4: Validated Adapter + Integration

#### T4.1: Implement ValidatedAdapter with retry

**Summary:** Create adapter that uses Pydantic validation with retry on failure.

**Owner:** Developer
**Estimate:** Medium
**Dependencies:** T1.2
**Milestone:** M4

**Files/modules:**
- `tinyagent/core/adapters.py` (modify)

**Implementation:**
```python
class ValidatedAdapter:
    max_retries: int = 2

    def format_request(self, tools: list[Tool], messages: list[dict]) -> dict:
        # No special request format - rely on prompt
        return {}

    def extract_tool_call(self, response: str) -> dict | None:
        # Use existing parse_json_response
        return parse_json_response(response)

    def validate_tool_call(self, payload: dict, tool: Tool) -> ValidationResult:
        # Pydantic validation of arguments
        ...
```

**Acceptance test:**
- Unit test: Invalid arguments trigger ValidationError with clear message.

---

#### T4.2: Implement ParsedAdapter (current behavior)

**Summary:** Wrap current JSON parsing as an adapter for fallback.

**Owner:** Developer
**Estimate:** Small
**Dependencies:** T1.2
**Milestone:** M4

**Files/modules:**
- `tinyagent/core/adapters.py` (modify)

**Implementation:**
```python
class ParsedAdapter:
    """Current JSON parsing approach - fallback adapter."""

    def format_request(self, tools: list[Tool], messages: list[dict]) -> dict:
        return {}

    def extract_tool_call(self, response: str) -> dict | None:
        return parse_json_response(response)
```

**Acceptance test:**
- Behavior matches current `parse_json_response` exactly.

---

#### T4.3: Add get_adapter factory function

**Summary:** Implement `get_adapter()` that selects best adapter based on model name.

**Owner:** Developer
**Estimate:** Small
**Dependencies:** T3.1, T4.1, T4.2
**Milestone:** M4

**Files/modules:**
- `tinyagent/core/adapters.py` (modify)

**Implementation:**
```python
def get_adapter(model: str, mode: ToolCallingMode = ToolCallingMode.AUTO) -> ToolCallingAdapter:
    if mode == ToolCallingMode.AUTO:
        if _supports_structured_outputs(model):
            return OpenAIStructuredAdapter()
        return ValidatedAdapter()

    return {
        ToolCallingMode.STRUCTURED: OpenAIStructuredAdapter(),
        ToolCallingMode.VALIDATED: ValidatedAdapter(),
        ToolCallingMode.PARSED: ParsedAdapter(),
    }[mode]

def _supports_structured_outputs(model: str) -> bool:
    """Check if model supports OpenAI structured outputs."""
    structured_prefixes = ("gpt-4o", "gpt-4.1", "o1", "o3")
    return any(model.startswith(p) for p in structured_prefixes)
```

**Acceptance test:**
- Unit test: `get_adapter("gpt-4o-mini")` returns OpenAIStructuredAdapter.

---

#### T4.4: Integrate adapters into ReactAgent

**Summary:** Update ReactAgent to use adapter for request formatting and response extraction.

**Owner:** Developer
**Estimate:** Medium
**Dependencies:** T4.3
**Milestone:** M4

**Files/modules:**
- `tinyagent/agents/react.py` (modify)

**Implementation:**
1. Add `tool_calling_mode: ToolCallingMode` parameter to ReactAgent
2. Initialize adapter in `__post_init__`
3. Use `adapter.format_request()` in `_chat()`
4. Replace `parse_json_response()` with `adapter.extract_tool_call()`
5. Add retry loop for ValidatedAdapter

```python
@dataclass(kw_only=True)
class ReactAgent(BaseAgent):
    tool_calling_mode: ToolCallingMode = ToolCallingMode.AUTO

    def __post_init__(self) -> None:
        super().__post_init__()
        # ... existing code ...
        self._adapter = get_adapter(self.model, self.tool_calling_mode)
```

**Acceptance test:**
- `uv run pytest tests/test_react_agent.py` passes with existing tests.

---

#### T4.5: Add Pydantic dependency

**Summary:** Add pydantic>=2.0 to pyproject.toml dependencies.

**Owner:** Developer
**Estimate:** Small
**Dependencies:** None
**Milestone:** M4

**Files/modules:**
- `pyproject.toml` (modify)

**Implementation:**
```toml
dependencies = [
    "openai>=1.0",
    "pydantic>=2.0",
    # ... rest unchanged
]
```

**Acceptance test:**
- `uv sync` succeeds, `uv run pytest` passes.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Pydantic migration breaks Tool users | High | Keep same `__call__` and `run()` API |
| OpenAI schema strict mode rejects valid calls | Medium | Fall back to ValidatedAdapter on error |
| Model detection false positives | Low | Conservative prefix matching, explicit mode override |
| JSON Schema generation edge cases | Medium | Comprehensive type mapping, fallback to "object" |

## Test Strategy

One test per task as specified in acceptance tests above. All tests focus on the core coding deliverable.

Key test files:
- `tests/test_schema.py` - JSON Schema conversion
- `tests/test_adapters.py` - Adapter implementations
- `tests/test_registry.py` - Updated Tool tests (existing)
- `tests/test_react_agent.py` - Integration tests (existing)

## References

### Research Doc Sections

- "What Pydantic AI Actually Does" - Key finding on approach
- "Recommended Approach for tinyAgent" - Hybrid strategy
- "Implementation Plan" - Phase breakdown
- "Code Examples" - Reference implementations

### Code References

- `tinyagent/core/parsing.py:15-29` - Current JSON parsing
- `tinyagent/core/registry.py:34-108` - Tool dataclass
- `tinyagent/agents/react.py:170-174` - parse_json_response usage
- `tinyagent/agents/react.py:320-332` - _chat method

---

## Final Gate

| Metric | Value |
|--------|-------|
| Plan path | `memory-bank/plan/2026-01-01_23-15-00_tool_calling_migration.md` |
| Milestone count | 4 |
| Task count | 10 |
| Tasks ready for coding | All (no external blockers) |

**Next command:** `/context-engineer:execute "memory-bank/plan/2026-01-01_23-15-00_tool_calling_migration.md"`
