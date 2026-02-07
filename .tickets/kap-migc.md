---
id: kap-migc
status: open
deps: []
links: []
created: 2026-02-03T21:36:20Z
type: epic
priority: 1
assignee: larock22
tags: [api, pythonic, breaking]
---
# Pythonic public API (streaming-first)

Make TinyAgent's public API feel idiomatic in Python: streaming via async iteration, prompt returns a value, utilities for extracting text, docs/examples follow the new style.

## Acceptance Criteria

- Primary README examples use async iteration (no callback subscription)
- Agent.prompt returns the final assistant message
- Agent.stream/stream_text are the recommended streaming APIs
- Helper to extract assistant text is public
