---
id: kap-04cd
status: closed
deps: []
links: []
created: 2026-02-01T17:42:57Z
type: task
priority: 2
tags: [mypy, types]
---
# Remove [Any] generic params and add ToolCall alias

Remove [Any] from Model and AgentTool type hints in agent.py:95,228,252,419. Add ToolCall = ToolCallContent alias to agent_types.py. Fixes ~5 mypy errors.

## Acceptance Criteria

mypy agent.py shows no generic parameter errors; proxy_types.py import succeeds; existing tests pass
