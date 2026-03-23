#!/usr/bin/env python3
"""Collect release debug artifacts for CI troubleshooting."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import zipfile
from pathlib import Path

from scripts.check_release_binding import check as check_release_binding
from scripts.check_release_wheels import check as check_release_wheels
from scripts.check_release_wheels import resolve_wheel_paths

ROOT = Path(__file__).resolve().parent.parent
WATCHED_DIRECTORIES = (
    ("dist", "dist"),
    ("wheelhouse", "wheelhouse"),
    ("tinyagent", "tinyagent"),
    (".artifact/raw-wheel", "raw_wheel"),
    (".external/tinyagent-alchemy/target/wheels", "external_binding_wheels"),
)


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _list_files(root: Path, relative_dir: str) -> list[str]:
    directory = root / relative_dir
    if not directory.exists():
        return []
    return sorted(_relative_to_root(path, root) for path in directory.rglob("*") if path.is_file())


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _safe_stem(filename: str) -> str:
    return filename.replace(".whl", "").replace("/", "_")


def _write_wheel_metadata(root: Path, output_dir: Path, wheel_path: Path) -> None:
    wheel_dir = output_dir / "wheels" / _safe_stem(wheel_path.name)

    with zipfile.ZipFile(wheel_path) as wheel:
        members = sorted(wheel.namelist())
        metadata_members = [name for name in members if name.endswith(".dist-info/WHEEL")]
        metadata_text = ""
        if len(metadata_members) == 1:
            metadata_text = wheel.read(metadata_members[0]).decode("utf-8")

    _write_text(
        wheel_dir / "summary.txt",
        "\n".join(
            [
                f"path: {_relative_to_root(wheel_path, root)}",
                f"members: {len(members)}",
            ]
        )
        + "\n",
    )
    _write_text(wheel_dir / "members.txt", "\n".join(members) + "\n")
    if metadata_text:
        _write_text(wheel_dir / "WHEEL", metadata_text)


def build_debug_artifact(*, root: Path = ROOT, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    listings = {
        label: _list_files(root, relative_dir) for relative_dir, label in WATCHED_DIRECTORIES
    }

    dist_dir = root / "dist"
    dist_wheels: list[Path] = []
    dist_wheel_note: str | None = None
    if dist_dir.exists():
        try:
            dist_wheels = resolve_wheel_paths([dist_dir])
            release_wheel_errors = check_release_wheels(dist_wheels)
        except RuntimeError as exc:
            release_wheel_errors = []
            dist_wheel_note = str(exc)
    else:
        release_wheel_errors = []
        dist_wheel_note = "no wheel files found"

    binding_errors = check_release_binding(
        pyproject_path=root / "pyproject.toml",
        package_dir=root / "tinyagent",
        require_present=False,
    )

    wheel_paths = []
    for relative_dir, _label in WATCHED_DIRECTORIES:
        wheel_paths.extend(sorted((root / relative_dir).glob("*.whl")))
    seen: set[Path] = set()
    unique_wheels: list[Path] = []
    for wheel_path in wheel_paths:
        if wheel_path not in seen:
            unique_wheels.append(wheel_path)
            seen.add(wheel_path)

    for wheel_path in unique_wheels:
        _write_wheel_metadata(root, output_dir, wheel_path)

    summary = {
        "machine": platform.machine(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "release_binding_check_errors": binding_errors,
        "release_wheel_check_errors": release_wheel_errors,
        "release_wheel_note": dist_wheel_note,
        "sys_platform": sys.platform,
        "watched_files": listings,
    }
    _write_json(output_dir / "summary.json", summary)

    _write_text(
        output_dir / "release_binding_check.txt",
        "\n".join(binding_errors) + ("\n" if binding_errors else "ok\n"),
    )

    wheel_check_lines = release_wheel_errors[:]
    if dist_wheel_note is not None:
        wheel_check_lines.append(f"note: {dist_wheel_note}")
    _write_text(
        output_dir / "release_wheel_check.txt",
        "\n".join(wheel_check_lines) + ("\n" if wheel_check_lines else "ok\n"),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / ".artifact" / "release-debug",
        help="Destination directory for the debug bundle.",
    )
    args = parser.parse_args()

    build_debug_artifact(output_dir=args.output_dir)
    print(f"release-debug-artifact: wrote {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
