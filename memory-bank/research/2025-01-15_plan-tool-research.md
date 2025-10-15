# Research – Plan Tool Implementation for AI Agent

**Date:** 2025-01-15
**Owner:** Claude Code Agent
**Phase:** Research
**Git Commit:** 98d35c8

## Goal
Research the tinyagent codebase to understand how to create a plan tool that can be passed to an AI agent to enable structured action planning and execution.

- Additional Search:
  - `grep -ri "plan" .claude/`
  - `grep -ri "scratchpad" examples/`
  - `grep -ri "sequence\|workflow" .claude/`

## Findings

### Core Tool System Architecture

**Relevant files & why they matter:**

- `/root/tinyAgent/tinyagent/core/registry.py` → **Heart of tool system** - Contains `@tool` decorator, `Tool` dataclass, and global registry
- `/root/tinyAgent/tinyagent/agents/react.py` → **Agent implementation** - ReactAgent orchestrates ReAct loop with tools
- `/root/tinyAgent/tinyagent/tools/builtin/web_search.py` → **Built-in tool example** - Shows proper tool implementation pattern
- `/root/tinyAgent/tinyagent/tools/validation.py` → **Tool validation** - Provides structure for validating tool classes
- `/root/tinyAgent/examples/react_demo.py` → **Multi-step workflow example** - Demonstrates sequential tool usage
- `/root/tinyAgent/tinyagent/core/types.py` → **Execution tracking** - RunResult and FinalAnswer types for state management

### Key Patterns / Solutions Found

**Tool Registration Pattern:**
```python
@tool
def create_plan(goal: str, steps: list[str]) -> dict:
    """Create a structured plan with steps for achieving a goal."""
    return {"goal": goal, "steps": steps, "status": "created"}
```

**Scratchpad Planning Pattern:**
- ReactAgent already supports scratchpad field in JSON payload for reasoning
- LLM can plan/reason without breaking execution flow
- Location: `/root/tinyAgent/tinyagent/agents/react.py:172-183`

**Multi-Step Coordination Pattern:**
- Trip planning example in `/root/tinyAgent/examples/react_demo.py:103-109`
- Uses LLM reasoning to sequence multiple tools (flights → weather → cost calculation)
- Shows natural language planning with tool coordination

**Safe Tool Execution Pattern:**
- Pre-validation using function signatures at `/root/tinyAgent/tinyagent/agents/react.py:309-339`
- Argument validation prevents runtime errors
- Graceful error handling with structured responses

**State Management Pattern:**
- Finalizer class provides atomic operations for final answers
- RunResult dataclass tracks execution metadata (steps, duration, state)
- Thread-safe singleton pattern for state management

**Temperature-Based Recovery Pattern:**
- Progressive temperature increase on errors (`TEMP_STEP = 0.2`)
- Adaptive strategy for handling parsing/execution failures
- Final attempt with zero temperature for graceful fallback

### Plan Tool Architecture Design

**Interface Design:**
```python
@tool
def create_plan(goal: str, context: str = "", max_steps: int = 10) -> dict:
    """Create a structured plan with steps for achieving a goal.

    Args:
        goal: The primary objective to accomplish
        context: Additional background information for planning
        max_steps: Maximum number of steps in the plan

    Returns:
        Plan object with goal, steps, and metadata
    """

@tool
def execute_plan(plan_id: str, start_step: int = 0) -> dict:
    """Execute a plan starting from a specific step.

    Args:
        plan_id: Identifier of the plan to execute
        start_step: Step index to start execution from

    Returns:
        Execution results with step-by-step progress
    """

@tool
def update_plan(plan_id: str, step_updates: dict) -> dict:
    """Update plan steps or status based on execution results.

    Args:
        plan_id: Identifier of the plan to update
        step_updates: Dictionary of step updates

    Returns:
        Updated plan with modified steps
    """
```

**Integration Points:**
- Leverage existing scratchpad pattern for plan reasoning
- Use RunResult pattern for tracking plan execution
- Integrate with safe tool execution for step validation
- Utilize finalizer pattern for managing plan completion

**Data Structures:**
```python
@dataclass
class PlanStep:
    description: str
    tool_name: str
    arguments: dict
    dependencies: list[int] = None
    status: str = "pending"  # pending, in_progress, completed, failed

@dataclass
class Plan:
    id: str
    goal: str
    steps: list[PlanStep]
    context: str = ""
    created_at: str = ""
    status: str = "created"  # created, executing, completed, failed
```

## Knowledge Gaps

**Missing context or details for next phase:**
- Need to determine plan persistence strategy (in-memory vs. file-based)
- Requires exploration of plan execution engine design (sequential vs. parallel)
- Need to research plan optimization and re-planning strategies
- Missing examples of complex tool dependencies and ordering constraints

## Implementation Considerations

**Leveraging Existing Patterns:**
1. **Scratchpad Integration** - Use existing scratchpad field for plan reasoning
2. **Registry System** - Plan tools auto-register via `@tool` decorator
3. **Safe Execution** - Validate plan steps using existing signature binding
4. **State Tracking** - Use RunResult pattern for plan execution metadata
5. **Error Recovery** - Apply temperature-based recovery to plan failures

**Key Architectural Decisions:**
- Plan tools should be composable with existing tools
- Leverage LLM for plan generation and adjustment
- Maintain backward compatibility with existing ReAct loop
- Use JSON payload interface for all plan operations
- Integrate with existing tool discovery and execution

## References

**Core Files for Full Review:**
- `/root/tinyAgent/tinyagent/core/registry.py` - Tool registration system
- `/root/tinyAgent/tinyagent/agents/react.py` - ReAct loop implementation
- `/root/tinyAgent/examples/react_demo.py` - Multi-step workflow example
- `/root/tinyAgent/tinyagent/core/types.py` - Execution tracking types
- `/root/tinyAgent/.claude/patterns/react_agent_improvements.md` - Improvement patterns

**Examples and Tests:**
- `/root/tinyAgent/examples/simple_demo.py` - Basic tool usage
- `/root/tinyAgent/tests/api_test/test_agent.py` - Agent integration tests
- `/root/tinyAgent/tinyagent/tools/builtin/web_search.py` - Tool implementation example

This research provides a solid foundation for implementing a plan tool that integrates seamlessly with the existing tinyagent architecture while leveraging established patterns for tool registration, execution, and error handling.