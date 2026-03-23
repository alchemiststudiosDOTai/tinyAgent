#!/usr/bin/env python3
"""Check built release wheels before publishing."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def resolve_wheel_paths(inputs: list[Path]) -> list[Path]:
    wheel_paths: list[Path] = []

    for input_path in inputs:
        if input_path.is_dir():
            wheel_paths.extend(sorted(path for path in input_path.glob("*.whl") if path.is_file()))
            continue

        if input_path.is_file() and input_path.suffix == ".whl":
            wheel_paths.append(input_path)
            continue

        raise RuntimeError(f"expected a wheel file or directory of wheels, got: {input_path}")

    if not wheel_paths:
        raise RuntimeError("no wheel files found")

    return wheel_paths


def _read_wheel_tags(wheel_path: Path) -> list[str]:
    with zipfile.ZipFile(wheel_path) as wheel:
        metadata_members = [name for name in wheel.namelist() if name.endswith(".dist-info/WHEEL")]
        if len(metadata_members) != 1:
            raise RuntimeError(
                f"{wheel_path.name} has {len(metadata_members)} .dist-info/WHEEL members"
            )

        metadata = wheel.read(metadata_members[0]).decode("utf-8")

    tags = []
    for line in metadata.splitlines():
        if line.startswith("Tag: "):
            tags.append(line.removeprefix("Tag: ").strip())

    if not tags:
        raise RuntimeError(f"{wheel_path.name} is missing wheel Tag metadata")

    return tags


def _find_generic_linux_tags(tags: list[str]) -> list[str]:
    generic_linux_tags: list[str] = []

    for tag in tags:
        parts = tag.split("-", 2)
        if len(parts) != 3:
            raise RuntimeError(f"invalid wheel tag: {tag}")

        platforms = parts[2].split(".")
        if any(platform.startswith("linux_") for platform in platforms):
            generic_linux_tags.append(tag)

    return generic_linux_tags


def check(wheel_paths: list[Path]) -> list[str]:
    errors: list[str] = []

    for wheel_path in wheel_paths:
        tags = _read_wheel_tags(wheel_path)
        generic_linux_tags = _find_generic_linux_tags(tags)
        if generic_linux_tags:
            errors.append(
                f"{wheel_path.name} uses generic Linux wheel tag(s) not accepted for PyPI: "
                + ", ".join(generic_linux_tags)
                + ". Repair Linux wheels with auditwheel before publishing."
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "wheel_path",
        type=Path,
        nargs="*",
        default=[Path("dist")],
        help="Wheel file(s), or directories containing wheel files. Defaults to dist/.",
    )
    args = parser.parse_args()

    try:
        wheel_paths = resolve_wheel_paths(args.wheel_path)
        errors = check(wheel_paths)
    except RuntimeError as exc:
        print(f"release-wheel-check: {exc}")
        return 1

    if errors:
        for error in errors:
            print(f"release-wheel-check: {error}")
        return 1

    print("release-wheel-check: wheel tags are publishable")
    for path in wheel_paths:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
