from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scripts.stage_release_binding import resolve_wheel_path, stage_binding


def _write_wheel(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as wheel:
        for name, data in members.items():
            wheel.writestr(name, data)


def test_resolve_wheel_path_accepts_single_wheel_directory(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "wheels"
    wheel_dir.mkdir()
    wheel_path = wheel_dir / "tinyagent_alchemy-1.2.7.whl"
    _write_wheel(wheel_path, {"tinyagent/_alchemy.abi3.so": b"binary"})

    resolved = resolve_wheel_path(wheel_dir)

    assert resolved == wheel_path


def test_stage_binding_replaces_existing_binding(tmp_path: Path) -> None:
    package_dir = tmp_path / "tinyagent"
    package_dir.mkdir()
    old_binding = package_dir / "_alchemy.old.pyd"
    old_binding.write_bytes(b"old")

    wheel_path = tmp_path / "tinyagent_alchemy-1.2.7.whl"
    _write_wheel(
        wheel_path,
        {
            "tinyagent/_alchemy.abi3.so": b"new-binary",
            "tinyagent/__init__.py": b"",
        },
    )

    staged = stage_binding(wheel_path, package_dir=package_dir)

    assert staged == package_dir / "_alchemy.abi3.so"
    assert staged.read_bytes() == b"new-binary"
    assert not old_binding.exists()


def test_stage_binding_rejects_missing_binding(tmp_path: Path) -> None:
    package_dir = tmp_path / "tinyagent"
    package_dir.mkdir()
    wheel_path = tmp_path / "tinyagent_alchemy-1.2.7.whl"
    _write_wheel(wheel_path, {"tinyagent/__init__.py": b""})

    with pytest.raises(RuntimeError, match="does not contain tinyagent/_alchemy"):
        stage_binding(wheel_path, package_dir=package_dir)


def test_stage_binding_rejects_multiple_candidates(tmp_path: Path) -> None:
    package_dir = tmp_path / "tinyagent"
    package_dir.mkdir()
    wheel_path = tmp_path / "tinyagent_alchemy-1.2.7.whl"
    _write_wheel(
        wheel_path,
        {
            "tinyagent/_alchemy.abi3.so": b"one",
            "tinyagent/_alchemy.pyd": b"two",
        },
    )

    with pytest.raises(RuntimeError, match="multiple tinyagent/_alchemy candidates"):
        stage_binding(wheel_path, package_dir=package_dir)
