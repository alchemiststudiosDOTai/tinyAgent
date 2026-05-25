---
title: Harness
when_to_read:
  - When changing repository quality gates
  - When checking what blocks a push or release
summary: Blocking hooks, release checks, and enforced rule entry points for this repository.
last_updated: "2026-04-04"
---

# HARNESS

## Pre-commit

- `ruff`: lint Python files and apply safe fixes when possible.
- `ruff-format`: enforce Python formatting.
- `trailing-whitespace`: remove trailing whitespace.
- `end-of-file-fixer`: ensure files end with a newline.
- `check-yaml`: validate YAML syntax.
- `check-added-large-files`: block oversized files from being committed.
- `check-merge-conflict`: catch unresolved merge markers.
- `py-compile`: run `python3 -m py_compile` on staged Python files to catch syntax and import-time compilation errors.
- `archlint`: run `python3 scripts/lint_architecture.py` to enforce architecture rules.
- `layer-lock`: run the import-boundary test at `tests/architecture/test_import_boundaries.py`.
- `mypy`: run static type checking with the repo's configured arguments.
- `vulture`: detect likely dead code in `tinyagent/`.
- `duplicate-code`: run pylint's duplicate-code detector on `tinyagent/`.
- `debtlint`: enforce ticketed technical-debt markers.
- `treelint`: enforce TinyAgent tree hygiene rules.
- `tinyagent-file-length`: block staged Python files under `tinyagent/` that exceed 700 lines.

## Pre-push

- `markdown-frontmatter-required`: run `uv run --group dev python scripts/check_markdown_frontmatter.py`
  to require `when_to_read`, `summary`, and `last_updated` frontmatter on repo-root
  Markdown files and every Markdown file under `docs/`, excluding `AGENTS.md`.
- Install the hook locally with `uv run --group dev python -m pre_commit install --hook-type pre-push`.
- CI should continue to enforce the same documentation contract as local hooks.

## Release

- `release-binding-check`: run `python3 scripts/check_release_binding.py --require-present` before building/publishing wheels that are expected to ship `_alchemy`.
- Build the binding from the in-repo crate at `rust/`, then stage the resulting `_alchemy` binary into `tinyagent/` before packaging.
- `release-wheel-check`: run `python3 scripts/check_release_wheels.py dist` before publishing.
  Linux wheels must not keep a generic `linux_*` tag; repair them with `auditwheel`
  until the wheel metadata reports `manylinux_*` or `musllinux_*` instead.
- `.github/workflows/publish-pypi.yml` is the release path for Linux, macOS, and Windows wheels:
  it builds the in-repo binding per-platform, stages it into `tinyagent/`, runs the release checks,
  repairs Linux wheels with `auditwheel` so PyPI receives a `manylinux` artifact,
  and publishes the release artifacts to PyPI via the repo `PYPI_TOKEN` secret.

## Ratchets

TBD

## Rules

TBD
