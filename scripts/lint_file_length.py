#!/usr/bin/env python3
"""Check that Python files do not exceed a configurable line-count limit."""

import argparse
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

MAX_LINES = 500


def get_max_lines() -> int:
    """Read max-file-lines from pyproject.toml if it exists."""
    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        config = tomllib.loads(pyproject.read_text())
        return config.get("tool", {}).get("lint", {}).get("max-file-lines", MAX_LINES)
    return MAX_LINES


def should_skip(path: Path) -> bool:
    """Skip cache and virtualenv artifacts."""
    return any(skip in str(path) for skip in [".ruff_cache", "__pycache__", ".venv"])


def iter_python_files(paths):
    """Resolve explicit files or discover Python files from the current tree."""
    if paths:
        return sorted(
            path
            for raw_path in paths
            for path in [Path(raw_path)]
            if path.suffix == ".py" and path.exists() and not should_skip(path)
        )
    return sorted(path for path in Path(".").rglob("*.py") if not should_skip(path))


def check_file_lengths(paths=None, max_lines=None):
    """Return list of (file, line_count, limit) for files exceeding the limit."""
    effective_max_lines = max_lines if max_lines is not None else get_max_lines()
    violations = []
    for path in iter_python_files(paths):
        line_count = len(path.read_text().splitlines())
        if line_count > effective_max_lines:
            violations.append((str(path), line_count, effective_max_lines))
    return sorted(violations, key=lambda x: -x[1])


def parse_args(argv) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--max-lines", type=int, default=None)
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])
    max_lines = args.max_lines if args.max_lines is not None else get_max_lines()
    violations = check_file_lengths(paths=args.paths, max_lines=max_lines)
    if violations:
        print(f"Files exceeding {max_lines} lines:")
        for filepath, count, limit in violations:
            print(f"  {filepath}: {count} lines (+{count - limit})")
        return 1
    print(f"All files under {max_lines} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
