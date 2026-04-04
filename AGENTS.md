# AGENTS.md

we are in the middle of bringing the rust binding back into this repo because the external split has caused too many issues
## Where To Start
- `README.md` — onboarding, install, examples, and current package usage notes.
- `docs/ARCHITECTURE.md` — module responsibilities, event flow, quality gates, technical-debt policy.
- `docs/api/README.md` — API reference index.
- `docs/releasing-alchemy-binding.md` — current release workflow and migration notes for wheels that ship `tinyagent._alchemy`.
- `HARNESS.md` — critical enforcement document for this repo: pre-commit hooks, ratchets, and rule entry points.
- `tests/architecture/test_import_boundaries.py` — enforced layer contract for the Python package.

## Repository Map
- `tinyagent/` — published Python package.
  - `__init__.py` — public exports.
  - `agent.py` — high-level `Agent` API and state management.
  - `agent_loop.py` — orchestration loop.
  - `agent_tool_execution.py` — concurrent tool execution.
  - `agent_types.py` — shared message, event, and state models.
  - `alchemy_provider.py` — Python bridge for the `tinyagent._alchemy` provider path.
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
- `python3 scripts/check_release_binding.py`
- `python3 scripts/check_release_binding.py --require-present` — run before building/publishing wheels that are expected to ship `_alchemy`
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
- Rust binding implementation work is allowed in this repo as part of the migration back from the external split.
- Keep Rust binding changes isolated from the core Python layer boundaries unless a cross-layer change is required.
- `tinyagent/__init__.py` is the public package surface; keep exports aligned with `scripts/lint_architecture.py` constraints.

## Sources Of Truth
- Product overview and examples: `README.md`
- Architecture and repo policies: `docs/ARCHITECTURE.md`
- API details: `docs/api/README.md`, `docs/api/*.md`
- Alchemy wheel-release workflow: `docs/releasing-alchemy-binding.md`
- Packaging/build config for this repo: `pyproject.toml`
- Critical repo enforcement harness: `HARNESS.md`
- Enforced checks: `.pre-commit-config.yaml`, `scripts/*.py`
- Import boundaries: `tests/architecture/test_import_boundaries.py`
- Harness-specific rules: `rules/README.md`, `rules/*.yml`
- Historical external binding repo: `https://github.com/alchemiststudiosDOTai/alchemy-rs`
- Do not file binding/runtime issues against `tunahorse/tinyagent-alchemy`; use `alchemiststudiosDOTai/alchemy-rs` if an external alchemy issue is needed during migration

## Change Guardrails
- Do not add `.env` loading or `dotenv` imports inside `tinyagent/`.
- Provider modules must not mutate `os.environ`.
- No free-form `TODO`/`FIXME`/`HACK`/`XXX`/`DEBT` markers; use the ticketed format documented in `docs/ARCHITECTURE.md` and enforced by `scripts/lint_debt.py`.
- Keep docs in this repo aligned with the Python package and the in-repo Rust binding migration status.
- Rust-binding source, build steps, and release rules may now live in this repo when they are part of restoring the binding here.
- During the migration, prefer keeping the Python-facing `tinyagent._alchemy` contract stable even if the build/release internals change.
- Treat `HARNESS.md` and the enforcement harness it describes as critical repo infrastructure. They are not optional process notes.
- If a codebase rule matters, record it in `HARNESS.md` and back it with a typed check, hook, script, test, or rule file.
- Prefer code-level enforcement over prose-only policy. Important rules should be enforced in `.pre-commit-config.yaml`, `scripts/*.py`, `tests/architecture/`, or `rules/` whenever practical.
- If you add or rename a governed package module, update `tests/architecture/test_import_boundaries.py`.
- If you change `docs/harness/`, rerun the ast-grep rules in `rules/`.

## Validation Checklist
- Every listed path still exists.
- Every listed command still matches current config, docs, or scripts.
- Docs are updated when public API, usage contracts, or Rust-binding ownership/build rules change.
- Release/build instructions match the actual binding workflow used by this repo.
- `HARNESS.md` stays aligned with the actual enforced hooks, ratchets, and rule entry points.
- Layer checks pass after import changes.
- `AGENTS.md` stays compact and points outward instead of duplicating docs.
