#!/usr/bin/env python3
"""
Pre-commit hook to check Python naming conventions.

Checks:
- Function names should be snake_case
- Class names should be PascalCase
- Constants should be UPPER_CASE
- Module imports should follow best practices
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple


class NamingChecker(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.errors: List[Tuple[int, str]] = []
        # Skip naming checks if this is the naming checker itself (has AST visitor methods)
        self.is_ast_visitor = "check_naming_conventions.py" in filename

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        """Check function names are snake_case."""
        # Skip this file entirely as it needs AST visitor method names
        if self.is_ast_visitor:
            self.generic_visit(node)
            return

        if not self._is_snake_case(node.name) and not node.name.startswith("_"):
            # Allow special methods like __init__, test methods
            if not (node.name.startswith("__") and node.name.endswith("__")):
                if not node.name.startswith("test_"):  # Allow pytest test functions
                    self.errors.append(
                        (node.lineno, f"Function '{node.name}' should be snake_case")
                    )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        """Check class names are PascalCase."""
        if not self._is_pascal_case(node.name):
            self.errors.append((node.lineno, f"Class '{node.name}' should be PascalCase"))
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        """Check constants are UPPER_CASE."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                # Check if it's a module-level constant (all caps with underscores)
                if (
                    self._is_upper_case(name)
                    and not self._is_snake_case(name)
                    and not self._is_pascal_case(name)
                ):
                    # This is likely intended as a constant, which is correct
                    pass
                elif name.isupper() and "_" in name and not self._is_proper_constant(name):
                    self.errors.append(
                        (node.lineno, f"Constant '{name}' should be UPPER_CASE with underscores")
                    )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        """Check import conventions."""
        if node.module and node.module == "tinyagent":
            # Only flag imports from the main tinyagent module (not submodules)
            for alias in node.names:
                name = alias.name
                # Flag importing snake_case functions from main module
                if (
                    self._is_snake_case(name)
                    and not name.startswith("_")
                    and name not in ["tool", "freeze_registry", "get_registry"]
                ):
                    self.errors.append(
                        (
                            node.lineno,
                            f"Importing function '{name}' from main module may violate separation of concerns. "
                            f"Consider using a submodule import instead.",
                        )
                    )
        self.generic_visit(node)

    @staticmethod
    def _is_snake_case(name: str) -> bool:
        """Check if name follows snake_case convention."""
        return re.match(r"^[a-z][a-z0-9_]*$", name) is not None

    @staticmethod
    def _is_pascal_case(name: str) -> bool:
        """Check if name follows PascalCase convention."""
        return re.match(r"^[A-Z][a-zA-Z0-9]*$", name) is not None

    @staticmethod
    def _is_upper_case(name: str) -> bool:
        """Check if name is UPPER_CASE."""
        return re.match(r"^[A-Z][A-Z0-9_]*$", name) is not None

    @staticmethod
    def _is_proper_constant(name: str) -> bool:
        """Check if name is a properly formatted constant."""
        return re.match(r"^[A-Z][A-Z0-9_]*[A-Z0-9]$", name) is not None


def check_file(filepath: Path) -> bool:
    """Check a single Python file for naming conventions."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filepath)
        checker = NamingChecker(str(filepath))
        checker.visit(tree)

        if checker.errors:
            print(f"\n{filepath}:")
            for line_no, message in checker.errors:
                print(f"  Line {line_no}: {message}")
            return False

        return True

    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}")
        return False
    except Exception as e:
        print(f"Error checking {filepath}: {e}")
        return False


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: check_naming_conventions.py <file1> [file2] ...")
        return 1

    all_good = True

    for filepath_str in sys.argv[1:]:
        filepath = Path(filepath_str)

        # Skip non-Python files
        if filepath.suffix != ".py":
            continue

        # Skip virtual environment and build directories
        if any(
            part.startswith(".") or part in ["venv", ".venv", "build", "dist", "__pycache__"]
            for part in filepath.parts
        ):
            continue

        if not check_file(filepath):
            all_good = False

    if not all_good:
        print("\n❌ Naming convention violations found!")
        print("Please fix the issues above before committing.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
