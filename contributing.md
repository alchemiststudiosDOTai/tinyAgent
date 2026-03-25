# Contributing to TinyAgent

TinyAgent is a small, typed, streaming-first agent framework for Python. This
repo also owns the in-repo Rust binding that backs the optional
`tinyagent._alchemy` runtime path.

Contributions here should keep the public Python contract coherent, preserve
the enforced module boundaries, and stay aligned with the repo's blocking
quality gates.

## Start Here

Read these before making non-trivial changes:

- `README.md` for package overview, installation, and examples
- `docs/ARCHITECTURE.md` for module responsibilities, event flow, and debt policy
- `docs/api/README.md` for the API reference index
- `HARNESS.md` for enforced hooks and release gates
- `docs/releasing-alchemy-binding.md` for wheel and binding release workflow
- `tests/architecture/test_import_boundaries.py` for the layer contract

## Local Setup

Use the repo's existing `uv` workflow:

```bash
uv sync --group dev
uv run pre-commit install
```

Python 3.10+ is required.

## Repo Map

- `tinyagent/`: published Python package
- `rust/`: in-repo crate that builds the optional `tinyagent._alchemy` binding
- `tests/`: unit, contract, release, and architecture tests
- `docs/`: architecture, API reference, release notes, and harness docs
- `docs/harness/`: live typed tool-call harness and harness-specific rules
- `scripts/`: custom enforcement, release, and smoke-check tooling
- `rules/`: ast-grep rules used for harness enforcement

Key package modules:

- `tinyagent/agent.py`: high-level `Agent` API and state handling
- `tinyagent/agent_loop.py`: orchestration loop
- `tinyagent/agent_tool_execution.py`: concurrent tool execution
- `tinyagent/agent_types.py`: shared runtime models and event types
- `tinyagent/alchemy_provider.py`: adapter for the optional `_alchemy` binding
- `tinyagent/rust_binding_provider.py`: Rust binding provider integration
- `tinyagent/proxy.py` and `tinyagent/proxy_event_handlers.py`: proxy streaming path
- `tinyagent/caching.py`: prompt caching helpers

## Design Rules

### Respect the layer map

The import graph is enforced in `tests/architecture/test_import_boundaries.py`.
Higher layers may depend on lower layers. The reverse is not allowed.

- Layer 3: `agent`
- Layer 2: `agent_loop`, `proxy`
- Layer 1: `agent_tool_execution`, `alchemy_provider`, `rust_binding_provider`,
  `proxy_event_handlers`, `caching`
- Layer 0: `agent_types`

`agent_types.py` must remain the leaf module among governed TinyAgent modules.

If you add or rename a governed package module, update the layer test in the
same change.

### Keep the public surface intentional

`tinyagent/__init__.py` is the package surface. Keep exports aligned with the
architecture linter and avoid expanding the root namespace casually.

Optional provider modules should be imported directly by callers when that is
the intended API. Do not bypass `scripts/lint_architecture.py`.

### Preserve the core architecture

The repo is built around a few stable ideas:

- streaming-first LLM interactions
- event-driven execution and state updates
- typed runtime models at boundaries
- clear separation between internal agent messages and LLM-boundary messages

Prefer changes that reinforce those constraints rather than weakening them with
special cases or implicit behavior.

### Provider modules are not config loaders

The architecture linter blocks these patterns in library code:

- no `.env` loading or `dotenv` imports inside `tinyagent/`
- no mutation of `os.environ` inside provider modules

Library code consumes configuration; it does not own process environment setup.

### Technical debt must be ticketed

Free-form `TODO`, `FIXME`, `HACK`, `XXX`, and `DEBT` markers are not allowed.
If you need a debt marker in Python code, tie it to a real ticket in `.tickets/`
using the documented format from `docs/ARCHITECTURE.md`.

### Prefer enforced rules over prose-only rules

If a lesson keeps repeating, encode it in structure:

- tests
- scripts
- pre-commit hooks
- ast-grep rules
- import-boundary checks

`HARNESS.md` is critical repo infrastructure, not optional process commentary.

## Working in the Rust Binding Migration

This repo is intentionally bringing the binding back in-tree. That changes where
the code lives, not the Python-facing contract contributors should preserve.

When you touch binding-related code:

- keep the `tinyagent._alchemy` contract stable unless a change is explicitly intended
- prefer isolating Rust and wheel-packaging work from the core Python layer graph
- update `docs/releasing-alchemy-binding.md`, `HARNESS.md`, and release checks if
  the binding build or packaging workflow changes

## What To Update With Your Change

Update code, tests, and docs together when behavior changes.

- Public API changes: update `README.md` and the relevant files under `docs/api/`
- Architecture or policy changes: update `docs/ARCHITECTURE.md`
- Release or wheel changes: update `docs/releasing-alchemy-binding.md`
- Harness changes: update `docs/harness/` and rerun the harness-specific rules
- Package surface changes: verify `tinyagent/__init__.py` still matches the
  intended public API and linter constraints

Do not leave docs trailing behind code changes in this repo.

## Validation

Run the checks that match your change. The core blockers are:

```bash
uv run pytest
uv run mypy --ignore-missing-imports --exclude "lint_file_length\\.py$" .
python3 scripts/lint_architecture.py
.venv/bin/python -m pytest tests/architecture/test_import_boundaries.py -x -q
uv run vulture --min-confidence 80 tinyagent
uv run pylint --disable=all --enable=duplicate-code tinyagent
python3 scripts/lint_debt.py
```

Useful local workflow:

```bash
uv run pre-commit run --all-files
```

Extra checks for specific change types:

If you touch release or wheel logic:

```bash
python3 scripts/check_release_binding.py
python3 scripts/check_release_binding.py --require-present
python3 scripts/check_release_wheels.py dist
```

If you touch `docs/harness/`:

```bash
uv run python docs/harness/tool_call_types_harness.py
sg scan -r rules/harness_no_duck_typing.yml docs/harness/
sg scan -r rules/harness_no_thin_protocols.yml docs/harness/
```

If you build or publish wheels that are expected to ship the binding, the
release gate in `HARNESS.md` applies: stage the built `_alchemy` artifact into
`tinyagent/` first, then run
`python3 scripts/check_release_binding.py --require-present`.

## Change Style

- Keep diffs focused and coherent
- Prefer deleting obsolete paths over adding compatibility layers
- Keep modules small enough to satisfy the file-length ceiling enforced under
  `tinyagent/`
- Do not commit cache directories or empty package directories under `tinyagent/`
- Add or update regression tests when fixing bugs or changing behavior

## Pull Requests

A good PR for this repo:

- explains the behavior change clearly
- names the checks you ran
- updates docs when the public contract changed
- avoids mixing unrelated cleanup with functional changes

If a rule matters enough to block future mistakes, do not stop at prose. Add or
update the corresponding test, script, hook, or rule file in the same change.
