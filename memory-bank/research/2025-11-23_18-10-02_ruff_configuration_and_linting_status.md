# Research – Ruff Configuration and Linting Status

**Date:** 2025-11-23
**Owner:** claude-research-agent
**Phase:** Research
**Git Commit:** 9b65a2e944b801bfdb7eda0e58f4eafe2d8951b3
**Branch:** master
**Last Updated:** 2025-11-23_18-10-02
**Tags:** [ruff, linting, code-quality, pre-commit]

## Goal
Summarize all *existing knowledge* about ruff configuration and linting setup before ensuring everything is properly linted.

- Additional Search:
  - `grep -ri "ruff" .claude/`
  - `find . -name "*.py" -exec ruff check {} \;`

## Findings
- **Relevant files & why they matter:**
  - `pyproject.toml` → Contains complete ruff configuration (lines 53-89)
  - `.pre-commit-config.yaml` → Pre-commit hook setup for ruff (lines 1-9)
  - `tinyagent/core/registry.py` → Has invalid `# noqa` directives that need fixing
  - `examples/code_demo.py` → Required reformatting (now fixed by pre-commit)
  - `examples/react_demo.py` → Required import reorganization (now fixed by pre-commit)
  - `tests/api_test/test_web_browse.py:129` → Needs `types-requests` for mypy type checking
  - `scripts/check_python_line_count.py` → Custom linting script for line limits
  - `scripts/check_naming_conventions.py` → Custom linting script for naming conventions

## Key Patterns / Solutions Found

- **Ruff Configuration Pattern**: Basic but effective setup with E, F, I rule sets
- **Line Length Standard**: 100 characters across all files
- **Python Version Target**: 3.10+ with support for 3.11, 3.12
- **Import Organization**: isort with `combine-as-imports = true`
- **Custom Enforcement**: 500-line limit per Python file, strict naming conventions
- **Pre-commit Integration**: Auto-fixing with `ruff --fix` and `ruff-format`
- **Security Linting**: Bandit integration with `-ll` (low level) security rules
- **Type Checking**: MyPy with relaxed settings, excludes certain directories

## Knowledge Gaps
- Missing rule categories that could improve code quality (W, BLE, NPE811, S, DT, A)
- No async-specific rules despite recent async conversion in codebase
- Invalid `# noqa` directives format in registry.py
- Optional type stubs dependency for better mypy coverage

## Current Status
- ✅ 42 Python files properly configured for linting
- ✅ Pre-commit hooks properly installed and working
- ✅ No active linting violations found
- ⚠️ 1 file has invalid `# noqa` directives (minor issue)
- ⚠️ Missing `types-requests` dependency for complete type checking

## References
- Ruff configuration: `pyproject.toml:53-89`
- Pre-commit setup: `.pre-commit-config.yaml:1-9`
- Custom linting scripts: `scripts/`
- Full file listing available in codebase-locator research output
