#!/usr/bin/env python3
"""Install a built wheel into a clean venv and import tinyagent._alchemy."""

from __future__ import annotations

import argparse
import os
import subprocess
import venv
from pathlib import Path


def resolve_wheel_path(input_path: Path) -> Path:
    if input_path.is_file() and input_path.suffix == ".whl":
        return input_path

    if input_path.is_dir():
        wheels = sorted(path for path in input_path.glob("*.whl") if path.is_file())
        if len(wheels) != 1:
            raise RuntimeError(
                f"expected exactly one wheel in {input_path}, found {len(wheels)}"
            )
        return wheels[0]

    raise RuntimeError(f"expected a wheel file or directory, got: {input_path}")


def smoke_test_wheel(wheel_path: Path) -> None:
    venv_dir = Path(".venv-smoke")
    venv.EnvBuilder(with_pip=True).create(venv_dir)

    scripts_dir = "Scripts" if os.name == "nt" else "bin"
    python_name = "python.exe" if os.name == "nt" else "python"
    smoke_python = venv_dir / scripts_dir / python_name

    subprocess.run([str(smoke_python), "-m", "pip", "install", str(wheel_path)], check=True)
    subprocess.run([str(smoke_python), "-c", "import tinyagent._alchemy"], check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "wheel_path",
        type=Path,
        nargs="?",
        default=Path("dist"),
        help="Wheel file or directory containing exactly one wheel. Defaults to dist/.",
    )
    args = parser.parse_args()

    try:
        wheel_path = resolve_wheel_path(args.wheel_path)
        smoke_test_wheel(wheel_path)
    except RuntimeError as exc:
        print(f"release-smoke-test: {exc}")
        return 1

    print(f"release-smoke-test: imported tinyagent._alchemy from {wheel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
