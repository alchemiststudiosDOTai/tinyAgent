---
id: kap-7bd7
status: closed
deps: []
links: []
created: 2026-02-07T18:41:27Z
type: epic
priority: 1
assignee: tunahorse1
tags: [lint, ci, precommit]
---
# Pre-commit: fix ruff + mypy failures

Make all pre-commit hooks pass on this repo. Current failures: ruff (E501 line too long, SIM110 loop -> any() in tinyagent/agent.py), ruff-format reformats files, and mypy type errors in proxy_event_handlers.py, openrouter_provider.py, proxy.py, agent.py.

## Acceptance Criteria

Running .venv/bin/pre-commit run --all-files exits 0 with no file modifications (clean git status).


## Notes

**2026-02-07T18:41:56Z**

Pre-commit status (2026-02-07):\n- ruff: tinyagent/agent.py E501 line too long at _AGENT_EVENT_HANDLERS Callable type; SIM110 in _has_meaningful_content loop.\n- ruff-format: reformatted tinyagent/agent.py.\n- mypy (7 errors): proxy_event_handlers.py stop_reason typeddict-item + unused ignore; openrouter_provider.py append(object) to list[str]; proxy.py context.messages cast/JsonValue assignment; agent.py extract_text called with object-typed msg.

**2026-02-07T18:43:00Z**

All hooks now pass: `.venv/bin/pre-commit run --all-files` exits 0 and a second run makes no modifications.
