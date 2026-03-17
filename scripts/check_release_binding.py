#!/usr/bin/env python3
"""Check the release contract for shipping the optional alchemy binding.

This repo does not own the Rust binding source, but release wheels can still ship
prebuilt `_alchemy` artifacts when those binaries are staged into `tinyagent/`
before packaging.
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
PACKAGE_DIR = ROOT / "tinyagent"
EXPECTED_PATTERNS = frozenset({"_alchemy*.so", "_alchemy*.pyd", "_alchemy*.dylib"})


def _load_tinyagent_package_data(pyproject_path: Path = PYPROJECT) -> set[str]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    tinyagent_data = (
        data.get("tool", {})
        .get("setuptools", {})
        .get("package-data", {})
        .get("tinyagent", [])
    )
    if not isinstance(tinyagent_data, list):
        return set()
    return {str(value) for value in tinyagent_data}


def _find_staged_binding_files(package_dir: Path = PACKAGE_DIR) -> list[Path]:
    files: list[Path] = []
    for pattern in EXPECTED_PATTERNS:
        files.extend(path for path in package_dir.glob(pattern) if path.is_file())
    return sorted(files)


def check(
    *,
    pyproject_path: Path = PYPROJECT,
    package_dir: Path = PACKAGE_DIR,
    require_present: bool = False,
) -> list[str]:
    package_data = _load_tinyagent_package_data(pyproject_path)
    errors: list[str] = []

    missing_patterns = sorted(EXPECTED_PATTERNS - package_data)
    if missing_patterns:
        errors.append(
            "pyproject.toml missing tinyagent package-data pattern(s): "
            + ", ".join(missing_patterns)
        )

    staged_files = _find_staged_binding_files(package_dir)
    if require_present and not staged_files:
        errors.append(
            "No staged `_alchemy` binary found in tinyagent/. "
            "Build the binding from the external tinyagent-alchemy repo and copy "
            "the resulting artifact into tinyagent/ before building release wheels."
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-present",
        action="store_true",
        help="Fail unless a staged `_alchemy` binary is present in tinyagent/.",
    )
    args = parser.parse_args()

    errors = check(require_present=args.require_present)
    if errors:
        for error in errors:
            print(f"release-binding-check: {error}")
        return 1

    print("release-binding-check: tinyagent package-data is configured for `_alchemy`")
    staged_files = _find_staged_binding_files()
    if staged_files:
        print("release-binding-check: staged binding artifacts:")
        for path in staged_files:
            print(f"  - {path.relative_to(ROOT)}")
    else:
        print(
            "release-binding-check: no staged binding artifacts found "
            "(ok unless --require-present is used)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
