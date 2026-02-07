---
id: kap-a2e3
status: closed
deps: []
links: []
created: 2026-02-07T18:41:42Z
type: task
priority: 3
assignee: tunahorse1
parent: kap-7bd7
tags: [mypy, types]
---
# Mypy: agent.py extract_text() argument type

Fix mypy error in tinyagent/agent.py where extract_text() is called with object-typed msg; narrow/cast to AgentMessage | None via runtime checks or typing fixes.

## Acceptance Criteria

mypy reports no errors for tinyagent/agent.py.
