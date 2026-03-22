#!/usr/bin/env python3
"""Stage the optional tinyagent._alchemy extension from a built wheel."""

from __future__ import annotations

import argparse
import fnmatch
import shutil
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = ROOT / "tinyagent"
EXPECTED_PATTERNS = ("_alchemy*.so", "_alchemy*.pyd", "_alchemy*.dylib")


def _is_binding_name(filename: str) -> bool:
    return any(fnmatch.fnmatch(filename, pattern) for pattern in EXPECTED_PATTERNS)


def _find_binding_members(wheel_path: Path) -> list[str]:
    with zipfile.ZipFile(wheel_path) as wheel:
        members = []
        for name in wheel.namelist():
            parts = PurePosixPath(name).parts
            if len(parts) >= 2 and parts[-2] == "tinyagent" and _is_binding_name(parts[-1]):
                members.append(name)
    return sorted(members)


def _remove_existing_staged_bindings(package_dir: Path) -> None:
    for pattern in EXPECTED_PATTERNS:
        for path in package_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def resolve_wheel_path(path: Path) -> Path:
    if path.is_file():
        if path.suffix != ".whl":
            raise RuntimeError(f"expected a .whl file, got: {path}")
        return path

    if path.is_dir():
        wheels = sorted(candidate for candidate in path.glob("*.whl") if candidate.is_file())
        if len(wheels) != 1:
            raise RuntimeError(f"expected exactly one wheel in {path}, found {len(wheels)}")
        return wheels[0]

    raise RuntimeError(f"wheel path does not exist: {path}")


def stage_binding(wheel_path: Path, package_dir: Path = PACKAGE_DIR) -> Path:
    members = _find_binding_members(wheel_path)
    if not members:
        raise RuntimeError(f"{wheel_path} does not contain tinyagent/_alchemy")
    if len(members) != 1:
        raise RuntimeError(
            f"{wheel_path} contains multiple tinyagent/_alchemy candidates: {', '.join(members)}"
        )

    member = members[0]
    destination = package_dir / PurePosixPath(member).name
    package_dir.mkdir(parents=True, exist_ok=True)
    _remove_existing_staged_bindings(package_dir)
    with zipfile.ZipFile(wheel_path) as wheel:
        with wheel.open(member) as src, destination.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "wheel_path",
        type=Path,
        help="Path to a tinyagent-alchemy wheel, or to a directory containing exactly one wheel.",
    )
    parser.add_argument(
        "--package-dir",
        type=Path,
        default=PACKAGE_DIR,
        help="Destination tinyagent package directory.",
    )
    args = parser.parse_args()

    wheel_path = resolve_wheel_path(args.wheel_path)
    staged_path = stage_binding(wheel_path, package_dir=args.package_dir)
    print(f"staged-binding: {staged_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
