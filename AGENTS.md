# AGENTS.md

## Project Overview
- TinyAgent ships a Python agent framework in `tinyagent/` plus a Rust PyO3 extension in `src/lib.rs` exposed as `tinyagent._alchemy`.
- Primary runtime path is the Rust-backed alchemy provider; the proxy provider remains available for server-managed backends.
- Treat this file as a quick map. For detailed behavior, defer to the docs and tests listed below.

## Where To Start
- `README.md` — onboarding, install, examples, Rust binding overview.
- `docs/ARCHITECTURE.md` — module responsibilities, event flow, quality gates, technical-debt policy.
- `docs/api/README.md` — API reference index.
- `tests/architecture/test_import_boundaries.py` — enforced layer contract for the Python package.

## Repository Map
- `tinyagent/` — published Python package.
  - `__init__.py` — public exports.
  - `agent.py` — high-level `Agent` API and state management.
  - `agent_loop.py` — orchestration loop.
  - `agent_tool_execution.py` — concurrent tool execution.
  - `agent_types.py` — shared message, event, and state models.
  - `alchemy_provider.py` — Rust-backed OpenAI-compatible provider bridge.
  - `proxy.py`, `proxy_event_handlers.py` — proxy streaming path.
  - `caching.py` — prompt caching helpers.
- `src/lib.rs` — canonical Rust binding for `tinyagent._alchemy`.
- `tests/` — unit and contract tests.
- `tests/architecture/` — import-boundary enforcement.
- `docs/api/` — per-module reference docs.
- `docs/harness/tool_call_types_harness.py` — live typed tool-call harness.
- `rules/` — ast-grep rules for `docs/harness/`.
- `scripts/` — custom lint/consistency checks and smoke scripts.
- `examples/` — runnable usage examples.
- `static/images/` — repo assets used by docs/README.

## Commands
- `uv run pytest`
- `uv run mypy --ignore-missing-imports --exclude "lint_file_length\\.py$" .`
- `python3 scripts/lint_architecture.py`
- `.venv/bin/python -m pytest tests/architecture/test_import_boundaries.py -x -q`
- `python3 scripts/lint_binding_drift.py`
- `uv run vulture --min-confidence 80 tinyagent`
- `uv run pylint --disable=all --enable=duplicate-code tinyagent`
- `python3 scripts/lint_debt.py`
- `uv run python docs/harness/tool_call_types_harness.py`
- `sg scan -r rules/harness_no_duck_typing.yml docs/harness/`
- `sg scan -r rules/harness_no_thin_protocols.yml docs/harness/`
- `maturin develop`
- `maturin develop --release`

## Boundaries
- Layer order is enforced in `tests/architecture/test_import_boundaries.py`:
  - Layer 3: `agent`
  - Layer 2: `agent_loop`, `proxy`
  - Layer 1: `agent_tool_execution`, `alchemy_provider`, `proxy_event_handlers`, `caching`
  - Layer 0: `agent_types`
- `agent_types.py` must remain the leaf module among governed TinyAgent modules.
- `src/lib.rs` is the single canonical Rust binding; do not reintroduce the retired duplicate binding directory or stale docs that point at it.
- `tinyagent/__init__.py` is the public package surface; keep exports aligned with `scripts/lint_architecture.py` constraints.

## Sources Of Truth
- Product overview and examples: `README.md`
- Architecture and repo policies: `docs/ARCHITECTURE.md`
- API details: `docs/api/README.md`, `docs/api/*.md`
- Packaging/build config: `pyproject.toml`, `Cargo.toml`
- Enforced checks: `.pre-commit-config.yaml`, `scripts/*.py`
- Import boundaries: `tests/architecture/test_import_boundaries.py`
- Harness-specific rules: `rules/README.md`, `rules/*.yml`

## Change Guardrails
- Do not add `.env` loading or `dotenv` imports inside `tinyagent/`.
- Provider modules must not mutate `os.environ`.
- No free-form `TODO`/`FIXME`/`HACK`/`XXX`/`DEBT` markers; use the ticketed format documented in `docs/ARCHITECTURE.md` and enforced by `scripts/lint_debt.py`.
- Keep docs aligned with the current binding name `tinyagent._alchemy`.
- If you add or rename a governed package module, update `tests/architecture/test_import_boundaries.py`.
- If you change `docs/harness/`, rerun the ast-grep rules in `rules/`.

## Validation Checklist
- Every listed path still exists.
- Every listed command still matches current config, docs, or scripts.
- Docs are updated when public API, usage contracts, or binding paths change.
- Layer checks pass after import changes.
- `AGENTS.md` stays compact and points outward instead of duplicating docs.
