from __future__ import annotations

from pathlib import Path

from setuptools import Distribution, setup


class TinyAgentDistribution(Distribution):
    """Mark wheels as platform-specific when a staged `_alchemy` binary exists."""

    def has_ext_modules(self) -> bool:  # type: ignore[override]
        package_dir = Path(__file__).resolve().parent / "tinyagent"
        patterns = ("_alchemy*.so", "_alchemy*.pyd", "_alchemy*.dylib")
        if any(path.is_file() for pattern in patterns for path in package_dir.glob(pattern)):
            return True
        return super().has_ext_modules()


setup(distclass=TinyAgentDistribution)
