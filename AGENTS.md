# AGENTS.md

## Project Overview
- TinyAgent is maintained here as a Python agent framework centered on `tinyagent/`.
- The Rust alchemy binding is no longer maintained in this repo; active binding work lives at `https://github.com/tunahorse/tinyagent-alchemy`.
- Primary runtime guidance in this repo should focus on the Python package surface and the proxy/provider glue that remains here.
- Treat this file as a quick map. For detailed behavior, defer to the docs and tests listed below.

## Where To Start
- `README.md` — onboarding, install, examples, and current package usage notes.
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
  - `alchemy_provider.py` — compatibility adapter for the optional external binding; do not treat this repo as the active home of that implementation.
  - `proxy.py`, `proxy_event_handlers.py` — proxy streaming path.
  - `caching.py` — prompt caching helpers.
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
- `uv run vulture --min-confidence 80 tinyagent`
- `uv run pylint --disable=all --enable=duplicate-code tinyagent`
- `python3 scripts/lint_debt.py`
- `uv run python docs/harness/tool_call_types_harness.py`
- `sg scan -r rules/harness_no_duck_typing.yml docs/harness/`
- `sg scan -r rules/harness_no_thin_protocols.yml docs/harness/`

## Boundaries
- Layer order is enforced in `tests/architecture/test_import_boundaries.py`:
  - Layer 3: `agent`
  - Layer 2: `agent_loop`, `proxy`
  - Layer 1: `agent_tool_execution`, `alchemy_provider`, `proxy_event_handlers`, `caching`
  - Layer 0: `agent_types`
- `agent_types.py` must remain the leaf module among governed TinyAgent modules.
- Do not reintroduce Rust binding implementation work in this repo; binding-specific changes belong in the separate binding repo.
- `tinyagent/__init__.py` is the public package surface; keep exports aligned with `scripts/lint_architecture.py` constraints.

## Sources Of Truth
- Product overview and examples: `README.md`
- Architecture and repo policies: `docs/ARCHITECTURE.md`
- API details: `docs/api/README.md`, `docs/api/*.md`
- Packaging/build config for this repo: `pyproject.toml`
- Enforced checks: `.pre-commit-config.yaml`, `scripts/*.py`
- Import boundaries: `tests/architecture/test_import_boundaries.py`
- Harness-specific rules: `rules/README.md`, `rules/*.yml`
- External binding repo: `https://github.com/tunahorse/tinyagent-alchemy`

## Change Guardrails
- Do not add `.env` loading or `dotenv` imports inside `tinyagent/`.
- Provider modules must not mutate `os.environ`.
- No free-form `TODO`/`FIXME`/`HACK`/`XXX`/`DEBT` markers; use the ticketed format documented in `docs/ARCHITECTURE.md` and enforced by `scripts/lint_debt.py`.
- Keep docs in this repo aligned with the Python package that lives here, and clearly mark any Rust-binding references as external or legacy.
- Do not add new Rust-binding source, build steps, or "source of truth" claims to this repo.
- If you add or rename a governed package module, update `tests/architecture/test_import_boundaries.py`.
- If you change `docs/harness/`, rerun the ast-grep rules in `rules/`.

## Validation Checklist
- Every listed path still exists.
- Every listed command still matches current config, docs, or scripts.
- Docs are updated when public API or usage contracts change, and any Rust-binding references make the external ownership clear.
- Layer checks pass after import changes.
- `AGENTS.md` stays compact and points outward instead of duplicating docs.
