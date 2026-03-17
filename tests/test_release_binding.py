from __future__ import annotations

from pathlib import Path

from scripts.check_release_binding import check


def _write_pyproject(path: Path, package_data: list[str]) -> None:
    path.write_text(
        "\n".join(
            [
                "[tool.setuptools.package-data]",
                "tinyagent = [" + ", ".join(f'\"{value}\"' for value in package_data) + "]",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_release_binding_check_passes_when_patterns_are_configured(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    package_dir = tmp_path / "tinyagent"
    package_dir.mkdir()
    _write_pyproject(pyproject, ["py.typed", "_alchemy*.so", "_alchemy*.pyd", "_alchemy*.dylib"])

    errors = check(pyproject_path=pyproject, package_dir=package_dir)

    assert errors == []


def test_release_binding_check_requires_staged_binary_when_requested(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    package_dir = tmp_path / "tinyagent"
    package_dir.mkdir()
    _write_pyproject(pyproject, ["py.typed", "_alchemy*.so", "_alchemy*.pyd", "_alchemy*.dylib"])

    errors = check(pyproject_path=pyproject, package_dir=package_dir, require_present=True)

    assert errors == [
        "No staged `_alchemy` binary found in tinyagent/. "
        "Build the binding from the external tinyagent-alchemy repo and copy "
        "the resulting artifact into tinyagent/ before building release wheels."
    ]


def test_release_binding_check_reports_missing_package_patterns(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    package_dir = tmp_path / "tinyagent"
    package_dir.mkdir()
    _write_pyproject(pyproject, ["py.typed", "_alchemy*.so"])

    errors = check(pyproject_path=pyproject, package_dir=package_dir)

    assert errors == [
        "pyproject.toml missing tinyagent package-data pattern(s): "
        "_alchemy*.dylib, _alchemy*.pyd"
    ]
