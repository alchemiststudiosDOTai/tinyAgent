# Small Wins Audit Plan

## Goals
- Identify quick-win improvements that can be implemented in under 30 minutes per PR
- Find dead code, orphaned files, naming inconsistencies, and lint drift
- Document findings without making any code modifications
- Prioritize by effort (XS/S) and impact (L/M/S)

## Constraints
- **Read-only**: No edits, no refactors, no PRs created
- Accept non-zero exits from lint/type tools
- Detection and documentation only

## Repository Snapshot
- **Branch**: master
- **Commit**: e59101b9ec4eda508febbba650305bca52b2e2da
- **Status**: Clean (1 untracked file: age.md)

## Codebase Overview
- **Package**: tiny-agent-os v0.73.5
- **Language**: Python (35 source files in tinyagent/)
- **Tests**: Located in tests/ (api_test/, prompt_test/)
- **Docs**: docs/ directory
- **Config**: pyproject.toml, ruff for linting

## Categories to Scan

### A. Structure & Naming
- Directory organization consistency
- File naming conventions (snake_case expected for Python)
- Duplicate or dead folders
- Module organization

### B. Dead Code & Orphans
- Unused Python symbols (functions, classes)
- Unreferenced files
- TODO/FIXME/HACK comments (tech debt markers)
- Orphaned test files or fixtures

### C. Lint & Config Drifts
- Ruff lint violations
- Type checking issues
- Import organization

### D. Micro-Performance/Clarity
- Functions exceeding 100 lines
- High cyclomatic complexity
- Hot paths by size

## Detection Tools
- `ruff check .` for Python linting
- `grep -r` for TODO/FIXME markers
- File analysis for dead code patterns
- Line counts for long functions
