#!/usr/bin/env python3
"""bindinglint: prevent Rust binding drift.

This project now has a single canonical Python extension binding:
- module: ``tinyagent._alchemy``
- Rust source: ``src/lib.rs``

This linter fails when legacy duplicate binding artifacts are reintroduced
(e.g. ``bindings/alchemy_llm_py``) or stale references to that path remain.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]  # Py<3.11 fallback

ROOT = Path(__file__).resolve().parents[1]
LEGACY_BINDING_DIR = ROOT / "bindings" / "alchemy_llm_py"
ROOT_PYPROJECT = ROOT / "pyproject.toml"
ROOT_RUST_BINDING = ROOT / "src" / "lib.rs"

LEGACY_MARKERS = (
    "bindings/alchemy_llm_py",
    'module-name = "alchemy_llm_py"',
)

SCAN_SUFFIXES = {
    ".md",
    ".py",
    ".toml",
    ".yaml",
    ".yml",
    ".rs",
}

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "target",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".grimp_cache",
}


def _iter_scan_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in SCAN_SUFFIXES:
            files.append(path)
    return files


def _check_root_binding_configuration(violations: list[str]) -> None:
    if not ROOT_PYPROJECT.exists():
        violations.append("missing pyproject.toml at repo root")
        return

    data = tomllib.loads(ROOT_PYPROJECT.read_text(encoding="utf-8"))
    module_name = data.get("tool", {}).get("maturin", {}).get("module-name")
    if module_name != "tinyagent._alchemy":
        violations.append("pyproject.toml [tool.maturin].module-name must be 'tinyagent._alchemy'")

    if not ROOT_RUST_BINDING.exists():
        violations.append("missing canonical binding source: src/lib.rs")
        return

    src = ROOT_RUST_BINDING.read_text(encoding="utf-8")
    if "fn _alchemy(" not in src:
        violations.append("src/lib.rs must expose #[pymodule] fn _alchemy(...)")


def _check_legacy_artifacts(violations: list[str]) -> None:
    if LEGACY_BINDING_DIR.exists():
        rel = LEGACY_BINDING_DIR.relative_to(ROOT)
        violations.append(f"legacy binding directory must not exist: {rel}")

    for path in _iter_scan_files(ROOT):
        rel = path.relative_to(ROOT)

        # This linter necessarily contains the legacy marker literals it checks for.
        if rel.as_posix() == "scripts/lint_binding_drift.py":
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in LEGACY_MARKERS:
            if marker not in text:
                continue
            for idx, line in enumerate(text.splitlines(), start=1):
                if marker in line:
                    violations.append(f"{rel}:{idx}: remove legacy marker: {marker}")


def main() -> int:
    violations: list[str] = []

    _check_root_binding_configuration(violations)
    _check_legacy_artifacts(violations)

    if not violations:
        print("bindinglint: all checks passed")
        return 0

    print(f"bindinglint: {len(violations)} violation(s) found")
    for violation in violations:
        print(f"- {violation}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
