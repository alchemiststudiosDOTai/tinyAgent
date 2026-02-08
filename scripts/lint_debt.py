#!/usr/bin/env python3
"""Technical debt tracker enforcement.

Rules (no nuance)
-----------------
1. Any technical debt annotation in Python code must be tied to a ticket in
   `.tickets/`.
2. No free-form TODO/FIXME/HACK/XXX/DEBT markers are allowed.

Allowed formats (must be uppercase):

    # TODO(tv-6ff4): short description
    # FIXME(kap-1103): short description
    # DEBT(tv-6ff4): short description

Enforcement:
- Scans all `*.py` files (excluding common cache/venv/build dirs).
- Extracts COMMENT tokens using `tokenize`.
- If a marker appears, it must match the allowed format and reference an
  existing, non-closed ticket file.
- Also verifies that docs/ARCHITECTURE.md contains the "Technical Debt" section.
"""

from __future__ import annotations

import re
import tokenize
from dataclasses import dataclass
from pathlib import Path

_MARKER_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX|DEBT)\b")
_VALID_RE = re.compile(
    r"(?P<marker>TODO|FIXME|HACK|XXX|DEBT)\((?P<ticket>[a-z]+-[0-9a-f]{4})\):\s+\S"
)

_SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "node_modules",
}


@dataclass(frozen=True)
class Violation:
    file: str
    line: int
    message: str


def _ticket_status(ticket_id: str) -> str | None:
    path = Path(".tickets") / f"{ticket_id}.md"
    if not path.exists():
        return None

    # Minimal YAML-front-matter parse: find `status: ...` near the top.
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    for line in lines[:60]:
        stripped = line.strip()
        if stripped.startswith("status:"):
            return stripped.split(":", 1)[1].strip()

    return None


def _check_debt_in_python_file(path: Path) -> list[Violation]:
    violations: list[Violation] = []

    try:
        with tokenize.open(path) as f:
            tokens = tokenize.generate_tokens(f.readline)
            for tok_type, tok_str, (line_no, _), _, _ in tokens:
                if tok_type != tokenize.COMMENT:
                    continue

                # Strip leading '#' and whitespace.
                comment = tok_str[1:].strip()
                if not comment:
                    continue

                for marker_match in _MARKER_RE.finditer(comment):
                    start = marker_match.start()
                    valid = _VALID_RE.match(comment[start:])
                    if not valid:
                        violations.append(
                            Violation(
                                file=str(path),
                                line=line_no,
                                message=(
                                    "Untracked debt marker. Use e.g. "
                                    "`# TODO(tv-6ff4): ...` (must reference a real ticket)."
                                ),
                            )
                        )
                        continue

                    ticket_id = valid.group("ticket")
                    status = _ticket_status(ticket_id)
                    if status is None:
                        violations.append(
                            Violation(
                                file=str(path),
                                line=line_no,
                                message=f"Debt marker references missing ticket '{ticket_id}'",
                            )
                        )
                    elif status == "closed":
                        violations.append(
                            Violation(
                                file=str(path),
                                line=line_no,
                                message=(
                                    f"Debt marker references closed ticket '{ticket_id}'. "
                                    "Remove the debt annotation or reopen the ticket."
                                ),
                            )
                        )

    except (OSError, UnicodeDecodeError, tokenize.TokenError) as e:
        violations.append(Violation(file=str(path), line=0, message=f"Failed to scan file: {e}"))

    return violations


def _check_architecture_doc() -> list[Violation]:
    doc = Path("docs/ARCHITECTURE.md")
    if not doc.exists():
        return [Violation(file=str(doc), line=0, message="docs/ARCHITECTURE.md not found")]

    content = doc.read_text(encoding="utf-8")

    required_substrings = [
        "## Technical Debt",
        "TODO(tv-",
        "No free-form TODO",
    ]

    missing = [s for s in required_substrings if s not in content]
    if not missing:
        return []

    return [
        Violation(
            file=str(doc),
            line=0,
            message=(
                f"ARCHITECTURE.md missing required Technical Debt documentation. Missing: {missing}"
            ),
        )
    ]


def check(directory: str = ".") -> list[Violation]:
    root = Path(directory)
    violations: list[Violation] = []

    for path in sorted(root.rglob("*.py")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        violations.extend(_check_debt_in_python_file(path))

    violations.extend(_check_architecture_doc())
    return violations


def main() -> int:
    violations = check()
    if not violations:
        print("debtlint: all checks passed")
        return 0

    for v in violations:
        loc = f"{v.file}:{v.line}" if v.line else v.file
        print(f"  {loc}  DEBT001  {v.message}")
    print(f"\ndebtlint: {len(violations)} violation(s) found")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
