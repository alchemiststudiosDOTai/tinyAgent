---
id: kap-b879
status: closed
deps: []
links: []
created: 2026-02-07T18:41:30Z
type: task
priority: 2
assignee: tunahorse1
parent: kap-7bd7
tags: [ruff, lint]
---
# Ruff: fix remaining lint in tinyagent/agent.py

Resolve E501 line-too-long and SIM110 any() suggestion flagged by ruff. Ensure ruff-format no longer modifies files.

## Acceptance Criteria

ruff + ruff-format hooks pass with no changes.
