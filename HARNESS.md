# HARNESS

## Pre-commit

- `ruff`: lint Python files and apply safe fixes when possible.
- `ruff-format`: enforce Python formatting.
- `trailing-whitespace`: remove trailing whitespace.
- `end-of-file-fixer`: ensure files end with a newline.
- `check-yaml`: validate YAML syntax.
- `check-added-large-files`: block oversized files from being committed.
- `check-merge-conflict`: catch unresolved merge markers.
- `archlint`: run `python3 scripts/lint_architecture.py` to enforce architecture rules.
- `layer-lock`: run the import-boundary test at `tests/architecture/test_import_boundaries.py`.
- `mypy`: run static type checking with the repo's configured arguments.
- `vulture`: detect likely dead code in `tinyagent/`.
- `duplicate-code`: run pylint's duplicate-code detector on `tinyagent/`.
- `debtlint`: enforce ticketed technical-debt markers.
- `treelint`: enforce TinyAgent tree hygiene rules.

## Pre-push

- No dedicated `pre-push` hook is currently configured in this repo.
- The architecture doc says the same blocking checks used in pre-commit should also run in CI.

## Ratchets

TBD

## Rules

TBD
