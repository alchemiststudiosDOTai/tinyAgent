"""Regression tests for documentation links."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_IGNORED_PREFIXES = ("http://", "https://", "mailto:", "#")


def _iter_local_links(markdown_text: str) -> list[str]:
    links: list[str] = []
    for raw_link in _LINK_PATTERN.findall(markdown_text):
        link = raw_link.strip()
        if not link or link.startswith(_IGNORED_PREFIXES):
            continue
        link = link.split("#", maxsplit=1)[0].strip()
        if not link:
            continue
        links.append(link)
    return links


@pytest.mark.parametrize(
    "doc_path",
    [
        Path("docs/README.md"),
        Path("docs/api/README.md"),
        Path("docs/api/providers.md"),
        Path("docs/api/openai-compatible-endpoints.md"),
        Path("docs/api/usage-semantics.md"),
    ],
)
def test_local_markdown_links_resolve(doc_path: Path) -> None:
    """All local markdown links in core docs pages should resolve from that page."""
    repo_root = Path(__file__).resolve().parents[1]
    page = repo_root / doc_path
    content = page.read_text(encoding="utf-8")

    missing: list[str] = []
    for link in _iter_local_links(content):
        target = (page.parent / link).resolve()
        if not target.exists():
            missing.append(f"{link} -> {target}")

    assert not missing, f"Broken links in {doc_path}:\n" + "\n".join(missing)
