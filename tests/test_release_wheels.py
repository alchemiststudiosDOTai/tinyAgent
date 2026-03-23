from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.check_release_wheels import check, resolve_wheel_paths


def _write_wheel(path: Path, tags: list[str]) -> None:
    wheel_metadata = [
        "Wheel-Version: 1.0",
        "Generator: tests",
        "Root-Is-Purelib: false",
        *[f"Tag: {tag}" for tag in tags],
        "",
    ]

    with zipfile.ZipFile(path, "w") as wheel:
        wheel.writestr("tiny_agent_os-1.2.16.dist-info/WHEEL", "\n".join(wheel_metadata))


def test_resolve_wheel_paths_accepts_directory(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "dist"
    wheel_dir.mkdir()
    wheel_path = wheel_dir / "tiny_agent_os-1.2.16-cp310-abi3-manylinux2014_x86_64.whl"
    _write_wheel(wheel_path, ["cp310-abi3-manylinux2014_x86_64"])

    resolved = resolve_wheel_paths([wheel_dir])

    assert resolved == [wheel_path]


def test_release_wheel_check_rejects_generic_linux_tags(tmp_path: Path) -> None:
    wheel_path = tmp_path / "tiny_agent_os-1.2.16-cp310-abi3-linux_x86_64.whl"
    _write_wheel(wheel_path, ["cp310-abi3-linux_x86_64"])

    errors = check([wheel_path])

    assert errors == [
        f"{wheel_path.name} uses generic Linux wheel tag(s) not accepted for PyPI: "
        "cp310-abi3-linux_x86_64. Repair Linux wheels with auditwheel before publishing."
    ]


def test_release_wheel_check_accepts_manylinux_tags(tmp_path: Path) -> None:
    wheel_path = (
        tmp_path / "tiny_agent_os-1.2.16-cp310-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl"
    )
    _write_wheel(
        wheel_path,
        [
            "cp310-abi3-manylinux2014_x86_64",
            "cp310-abi3-manylinux_2_17_x86_64",
        ],
    )

    errors = check([wheel_path])

    assert errors == []


def test_release_wheel_check_accepts_macos_and_windows_tags(tmp_path: Path) -> None:
    macos_wheel = tmp_path / "tiny_agent_os-1.2.16-cp310-abi3-macosx_14_0_arm64.whl"
    windows_wheel = tmp_path / "tiny_agent_os-1.2.16-cp310-abi3-win_amd64.whl"
    _write_wheel(macos_wheel, ["cp310-abi3-macosx_14_0_arm64"])
    _write_wheel(windows_wheel, ["cp310-abi3-win_amd64"])

    errors = check([macos_wheel, windows_wheel])

    assert errors == []
