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

- No dedicated `pre-push` hook is currently configured in this repo.
- The architecture doc says the same blocking checks used in pre-commit should also run in CI.

## Release

- `release-binding-check`: run `python3 scripts/check_release_binding.py --require-present` before building/publishing wheels that are expected to ship `_alchemy`.
- `release-binding-check` also verifies that any staged `_alchemy` artifact matches the host
  platform binary format, so run it on the target release platform before packaging.
- `stage-release-binding`: run `python3 scripts/stage_release_binding.py <tinyagent-alchemy wheel-or-wheel-dir>`
  to replace any stale local `_alchemy` artifact with the wheel-built binding before packaging.
  The current external wheel layout is `_alchemy/_alchemy.abi3.so`, and the staging script
  accepts that packaged layout.
- `.github/workflows/release-platform-wheels.yml` is the release path for Linux, macOS, and Windows wheels:
  it builds the external binding per-platform, stages it into `tinyagent/`, runs the release check,
  pins `OPENSSL_SRC_PERL` and `PERL` to `C:\Strawberry\perl\bin\perl.exe` on Windows so vendored
  OpenSSL does not depend on runner PATH ordering, builds the TinyAgent wheel, smoke-tests
  `import tinyagent._alchemy` from a clean venv, and
  publishes the release artifacts to PyPI on tag builds or manual dispatch via the repo `PYPI_TOKEN` secret.
- This repo still does not own the Rust binding source; build the binary from `https://github.com/tunahorse/tinyagent-alchemy`, then stage the artifact into `tinyagent/` so setuptools packages it.

## Ratchets

TBD

## Rules

TBD
