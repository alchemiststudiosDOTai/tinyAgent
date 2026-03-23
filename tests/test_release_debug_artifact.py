from __future__ import annotations

import json
import zipfile
from pathlib import Path

from scripts.build_release_debug_artifact import build_debug_artifact


def _write_pyproject(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "[tool.setuptools.package-data]",
                'tinyagent = ["py.typed", "_alchemy*.so", "_alchemy*.pyd", "_alchemy*.dylib"]',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_wheel(path: Path, tags: list[str]) -> None:
    wheel_metadata = [
        "Wheel-Version: 1.0",
        "Generator: tests",
        "Root-Is-Purelib: false",
        *[f"Tag: {tag}" for tag in tags],
        "",
    ]

    with zipfile.ZipFile(path, "w") as wheel:
        wheel.writestr("tiny_agent_os-1.2.17.dist-info/WHEEL", "\n".join(wheel_metadata))
        wheel.writestr("tiny_agent_os-1.2.17.dist-info/RECORD", "")
        wheel.writestr("tinyagent/__init__.py", "")


def test_build_debug_artifact_writes_summary_and_wheel_metadata(tmp_path: Path) -> None:
    root = tmp_path
    output_dir = root / ".artifact" / "release-debug"
    (root / "tinyagent").mkdir()
    (root / "dist").mkdir()
    _write_pyproject(root / "pyproject.toml")

    wheel_path = root / "dist" / "tiny_agent_os-1.2.17-cp310-abi3-linux_x86_64.whl"
    _write_wheel(wheel_path, ["cp310-abi3-linux_x86_64"])

    build_debug_artifact(root=root, output_dir=output_dir)

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["release_wheel_check_errors"] == [
        "tiny_agent_os-1.2.17-cp310-abi3-linux_x86_64.whl uses generic Linux wheel tag(s) "
        "not accepted for PyPI: cp310-abi3-linux_x86_64. Repair Linux wheels with auditwheel "
        "before publishing."
    ]
    assert summary["watched_files"]["dist"] == [
        "dist/tiny_agent_os-1.2.17-cp310-abi3-linux_x86_64.whl"
    ]

    wheel_debug_dir = output_dir / "wheels" / "tiny_agent_os-1.2.17-cp310-abi3-linux_x86_64"
    assert (
        (wheel_debug_dir / "WHEEL")
        .read_text(encoding="utf-8")
        .strip()
        .endswith("Tag: cp310-abi3-linux_x86_64")
    )
    assert "tinyagent/__init__.py" in (wheel_debug_dir / "members.txt").read_text(encoding="utf-8")


def test_build_debug_artifact_handles_missing_dist_wheels(tmp_path: Path) -> None:
    root = tmp_path
    output_dir = root / ".artifact" / "release-debug"
    (root / "tinyagent").mkdir()
    _write_pyproject(root / "pyproject.toml")

    build_debug_artifact(root=root, output_dir=output_dir)

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["release_wheel_check_errors"] == []
    assert summary["release_wheel_note"] == "no wheel files found"
    assert (output_dir / "release_wheel_check.txt").read_text(encoding="utf-8") == (
        "note: no wheel files found\n"
    )
