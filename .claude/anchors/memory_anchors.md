# Memory Anchors Registry

## Purpose
This file maintains a registry of memory anchors used throughout the codebase for precise reference by Claude instances.

## Anchor Format
`CLAUDE-ANCHOR-[UUID]-[SEMANTIC-TAG]`

## Active Anchors

### Core System Anchors
- `CLAUDE-ANCHOR-7f8a9b0c-AGENT-MAIN`: ReactAgent main execution loop (tinyagent/agents/agent.py:85)
- `CLAUDE-ANCHOR-1d2e3f4g-CODE-AGENT`: TinyCodeAgent execution logic (tinyagent/agents/code_agent.py:219)
- `CLAUDE-ANCHOR-5h6i7j8k-TOOL-REGISTRY`: Global tool registration system (tinyagent/tools.py:45)

### Critical Functions
- `CLAUDE-ANCHOR-9l0m1n2o-FINALIZER`: Final answer tracking (tinyagent/finalizer.py:12)
- `CLAUDE-ANCHOR-3p4q5r6s-STEP-LIMIT`: Step limit handling (tinyagent/exceptions.py:18)
- `CLAUDE-ANCHOR-7t8u9v0w-RUN-RESULT`: Execution result structure (tinyagent/types.py:25)

### Known Problem Areas
- `CLAUDE-ANCHOR-2x3y4z5a-FINAL-ATTEMPT`: Edge case in final answer parsing (tinyagent/agents/code_agent.py:364)

## Usage
Reference these anchors in queries like:
"Check the error handling at CLAUDE-ANCHOR-e5f6g7h8-ERROR-HANDLER"

## Maintenance
- Add new anchors when identifying critical code sections
- Remove obsolete anchors during refactoring
- Update line numbers when code moves
