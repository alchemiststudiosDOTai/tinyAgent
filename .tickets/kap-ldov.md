---
id: kap-ldov
status: closed
deps: []
links: []
created: 2026-02-03T21:36:27Z
type: task
priority: 1
assignee: larock22
parent: kap-migc
tags: [api, pythonic]
---
# Return values from Agent.prompt()/continue_() and add Agent.stream()

## Acceptance Criteria

- Agent.prompt returns final assistant message
- Agent.continue_ returns final assistant message
- Agent.stream yields AgentEvent
