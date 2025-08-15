#!/usr/bin/env python3
"""
Pre-commit hook script to check Python file line counts.

This script enforces a 500-line limit on all Python files in the repository,
excluding the venv directory.
"""

import sys
from pathlib import Path


def find_python_files(root_path: Path) -> list[Path]:
    """Find all Python files recursively, excluding venv directories."""
    python_files = []

    # Walk through all files recursively
    for file_path in root_path.rglob("*.py"):
        # Skip files in venv directories
        if any(
            part.startswith(".") or part in ["venv", ".venv", "build", "dist", "__pycache__"]
            for part in file_path.parts
        ):
            continue
        python_files.append(file_path)

    return python_files


def count_lines(file_path: Path) -> int:
    """Count the number of lines in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0


def check_line_counts(files: list[Path], max_lines: int = 500) -> bool:
    """Check if any file exceeds the maximum line count."""
    violations = []

    for file_path in files:
        line_count = count_lines(file_path)
        if line_count > max_lines:
            violations.append((file_path, line_count))

    # Report violations
    if violations:
        print(
            f"ERROR: Found {len(violations)} file(s) exceeding {max_lines} lines:", file=sys.stderr
        )
        for file_path, line_count in violations:
            print(f"  {file_path}: {line_count} lines", file=sys.stderr)
        return False

    return True


def main():
    """Main function to run the pre-commit hook."""
    if len(sys.argv) > 1:
        # If files are passed as arguments, check only those files
        python_files = []
        for arg in sys.argv[1:]:
            file_path = Path(arg)
            if file_path.suffix == ".py":
                python_files.append(file_path)
    else:
        # Get the repository root (current working directory)
        repo_root = Path.cwd()
        # Find all Python files
        python_files = find_python_files(repo_root)

    # Check line counts
    if not check_line_counts(python_files):
        # Exit with error code if violations found
        sys.exit(1)

    # Success
    print("All Python files are within the line limit.")
    sys.exit(0)


if __name__ == "__main__":
    main()
