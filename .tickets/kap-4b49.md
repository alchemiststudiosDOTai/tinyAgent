---
id: kap-4b49
status: closed
deps: []
links: []
created: 2026-02-01T17:42:53Z
type: task
priority: 2
tags: [mypy, types]
---
# Add missing fields to AssistantMessage dataclass

Add fields to AssistantMessage in agent_types.py:84-92: api, provider, model, usage, errorMessage. Also expand stopReason literals. Fixes ~10 mypy errors.

## Acceptance Criteria

mypy agent.py shows no AssistantMessage attribute errors; existing tests pass
