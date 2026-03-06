#!/usr/bin/env python3
"""Enforce tinyagent package tree hygiene.

Rules:
- no `__pycache__` directories under `tinyagent/`
- no empty (or cache-only) directories under `tinyagent/`
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path("tinyagent")


@dataclass(frozen=True)
class Violation:
    path: Path
    code: str
    message: str


def _iter_dirs(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_dir())


def _has_non_cache_children(directory: Path) -> bool:
    return any(child.name != "__pycache__" for child in directory.iterdir())


def check(root: Path = ROOT) -> list[Violation]:
    if not root.exists() or not root.is_dir():
        return [Violation(path=root, code="TREE000", message="tinyagent/ directory not found")]

    violations: list[Violation] = []
    for directory in _iter_dirs(root):
        if directory.name == "__pycache__":
            violations.append(
                Violation(
                    path=directory,
                    code="TREE001",
                    message="Remove __pycache__ directory from tinyagent/",
                )
            )
            continue

        if not _has_non_cache_children(directory):
            violations.append(
                Violation(
                    path=directory,
                    code="TREE002",
                    message="Remove empty/cache-only directory from tinyagent/",
                )
            )

    return violations


def main() -> int:
    violations = check()
    if not violations:
        print("treelint: tinyagent tree is clean")
        return 0

    for violation in violations:
        print(f"{violation.path}  {violation.code}  {violation.message}")

    print("\nCleanup:")
    print("  find tinyagent -type d -name '__pycache__' -prune -exec rm -rf {} +")
    print("  find tinyagent -depth -type d -empty ! -path 'tinyagent' -delete")
    print(f"\ntreelint: {len(violations)} violation(s) found")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
