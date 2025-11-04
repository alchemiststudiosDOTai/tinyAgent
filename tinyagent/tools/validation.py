"""
Utilities for validating built-in tool classes.

The validator performs a static analysis using the Python AST to ensure tool
implementations stay simple, deterministic, and easy to serialize. It checks:

* Class-level attributes are assigned literal data (strings, numbers, dicts, etc.).
* `__init__` declarations provide literal defaults for every parameter.
* Method bodies do not reference undefined names or rely on implicit globals.

Violations raise :class:`ToolValidationError` with a consolidated list of issues.
"""

from __future__ import annotations

import ast
import builtins
import inspect
import textwrap
from dataclasses import dataclass
from typing import Iterable, Sequence, Set

__all__ = ["ToolValidationError", "validate_tool_class"]


class ToolValidationError(ValueError):
    """Raised when a tool class fails structural validation."""


_BUILTIN_NAMES: Set[str] = set(dir(builtins))


def validate_tool_class(cls: type) -> None:
    """
    Validate that a tool class follows serialization-friendly conventions.

    Parameters
    ----------
    cls:
        The class object to validate.

    Raises
    ------
    ToolValidationError
        If the class violates any of the safety constraints.
    """

    module = inspect.getmodule(cls)
    if module is None:
        raise ToolValidationError(f"Cannot locate module for {cls!r}.")

    try:
        module_source = inspect.getsource(module)
    except OSError as exc:  # pragma: no cover - defensive guard
        raise ToolValidationError(
            f"Unable to read source for module {module.__name__}: {exc}"
        ) from exc

    module_tree = ast.parse(textwrap.dedent(module_source))
    module_names = _collect_module_names(module_tree)
    class_node = _find_class_node(module_tree, cls.__name__)

    if class_node is None:
        raise ToolValidationError(f"Could not find class definition for {cls.__name__!r}.")

    errors: list[str] = []
    errors.extend(_validate_class_body(class_node))
    errors.extend(_validate_init_signature(class_node))
    errors.extend(_validate_methods(class_node, module_names))

    if errors:
        details = "\n- ".join(errors)
        raise ToolValidationError(f"{cls.__name__} validation failed:\n- {details}")


def _collect_module_names(module_tree: ast.Module) -> Set[str]:
    names: Set[str] = set()
    for node in module_tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    # Star imports make static tracking unreliable.
                    names.add("*")
                else:
                    names.add(alias.asname or alias.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif node.target is not None:
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _find_class_node(tree: ast.Module, class_name: str) -> ast.ClassDef | None:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _validate_class_body(class_node: ast.ClassDef) -> list[str]:
    errors: list[str] = []
    for index, stmt in enumerate(class_node.body):
        if _is_docstring(index, stmt):
            continue
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            errors.extend(_validate_class_assignment(stmt))
            continue
        errors.append(
            f"Unsupported statement '{stmt.__class__.__name__}' in class body (line {stmt.lineno})."
        )
    return errors


def _is_docstring(index: int, stmt: ast.stmt) -> bool:
    if index != 0 or not isinstance(stmt, ast.Expr):
        return False
    value = stmt.value
    return isinstance(value, ast.Constant) and isinstance(value.value, str)


def _validate_class_assignment(node: ast.Assign | ast.AnnAssign) -> list[str]:
    errors: list[str] = []
    targets: Sequence[ast.expr]
    value: ast.expr | None

    if isinstance(node, ast.Assign):
        targets = node.targets
        value = node.value
    else:
        targets = [node.target] if node.target is not None else []
        value = node.value

    for target in targets:
        if isinstance(target, ast.Name):
            pass
        else:
            errors.append(
                f"Class attributes must assign to names; found {target.__class__.__name__} (line {target.lineno})."
            )
    if value is not None and not _is_literal(value):
        errors.append(
            f"Class attribute values must be literals; found {value.__class__.__name__} (line {value.lineno})."
        )
    return errors


def _validate_init_signature(class_node: ast.ClassDef) -> list[str]:
    for stmt in class_node.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
            return _check_init(stmt)
    return ["Tool classes must define an __init__ method."]


def _check_init(func: ast.FunctionDef) -> list[str]:
    errors: list[str] = []

    args = func.args
    if args.posonlyargs:
        errors.append("__init__ cannot use positional-only parameters.")

    if args.vararg is not None or args.kwarg is not None:
        errors.append("__init__ cannot accept *args or **kwargs.")

    positional = list(args.args)
    if not positional or positional[0].arg != "self":
        errors.append("__init__ must declare 'self' as the first parameter.")

    params = positional[1:]
    defaults = args.defaults
    if len(defaults) != len(params):
        errors.append("__init__ parameters must all provide default literal values.")
    else:
        for param, default in zip(params, defaults, strict=False):
            if not _is_literal(default):
                errors.append(
                    f"Default for parameter '{param.arg}' must be a literal (line {default.lineno})."
                )

    for kwonly, default in zip(args.kwonlyargs, args.kw_defaults or [], strict=False):
        if default is None:
            errors.append(
                f"Keyword-only parameter '{kwonly.arg}' must have a default literal value."
            )
        elif not _is_literal(default):
            errors.append(
                f"Default for keyword-only parameter '{kwonly.arg}' must be a literal (line {default.lineno})."
            )

    return errors


def _validate_methods(class_node: ast.ClassDef, module_names: Set[str]) -> list[str]:
    errors: list[str] = []
    for stmt in class_node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            analyzer = _function_analyzer(module_names, stmt)
            analyzer.visit_block(stmt.body)
            errors.extend(analyzer.errors)
    return errors


def _is_literal(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(_is_literal(elt) for elt in node.elts)
    if isinstance(node, ast.Dict):
        return all(
            (key is None or _is_literal(key))
            and _is_literal(value)  # key is None for dict unpacking
            for key, value in zip(node.keys, node.values, strict=False)
        )
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return _is_literal(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        return _is_literal(node.left) and _is_literal(node.right)
    if isinstance(node, ast.NamedExpr):
        return False
    return False


@dataclass
class _function_analyzer(ast.NodeVisitor):
    module_names: Set[str]
    function: ast.FunctionDef | ast.AsyncFunctionDef

    def __post_init__(self) -> None:
        params = {arg.arg for arg in self.function.args.args}
        params.update(arg.arg for arg in self.function.args.kwonlyargs)
        if self.function.args.vararg:
            params.add(self.function.args.vararg.arg)
        if self.function.args.kwarg:
            params.add(self.function.args.kwarg.arg)
        self._defined: Set[str] = params
        self.errors: list[str] = []

    # Public API ---------------------------------------------------------
    def visit_block(self, statements: Iterable[ast.stmt]) -> None:
        for stmt in statements:
            if self._is_docstring(stmt):
                continue
            self.visit(stmt)

    # AST visitors -------------------------------------------------------
    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            if not self._is_allowed_name(node.id):
                self.errors.append(
                    f"Undefined name '{node.id}' in {self.function.name} (line {node.lineno})."
                )
        elif isinstance(node.ctx, (ast.Store, ast.Param)):
            self._defined.add(node.id)
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        self.errors.append(f"Global declarations are not allowed (line {node.lineno}).")

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.errors.append(f"Nonlocal declarations are not allowed (line {node.lineno}).")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        self.visit(node.value)
        # Attribute names are fine if the base expression is valid.

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self.errors.append(f"Lambdas are not allowed in method bodies (line {node.lineno}).")

    def visit_Call(self, node: ast.Call) -> None:
        self.visit(node.func)
        for arg in node.args:
            self.visit(arg)
        for keyword in node.keywords:
            if keyword.value is None:
                continue
            self.visit(keyword.value)

    def visit_Assign(self, node: ast.Assign) -> None:
        # Check for assignments to None that need type annotations
        if isinstance(node.value, ast.Constant) and node.value.value is None:
            for target in node.targets:
                if isinstance(target, (ast.Name, ast.Attribute)) and not isinstance(
                    target.ctx, ast.Load
                ):
                    # This is a simple assignment to None without type annotation
                    # We need to check if this is in a method body (like __init__)
                    if hasattr(self, "function") and self.function.name == "__init__":
                        self.errors.append(
                            f"Assignment to None requires type annotation (line {node.lineno})."
                        )

        for target in node.targets:
            if isinstance(target, ast.Name):
                self._defined.add(target.id)
        self.visit(node.value)

    def generic_visit(self, node: ast.AST) -> None:
        super().generic_visit(node)

    # Helpers ------------------------------------------------------------
    def _is_allowed_name(self, name: str) -> bool:
        if name in self._defined:
            return True
        if name in _BUILTIN_NAMES:
            return True
        if "*" in self.module_names:
            return True
        return name in self.module_names

    @staticmethod
    def _is_docstring(stmt: ast.stmt) -> bool:
        if not isinstance(stmt, ast.Expr):
            return False
        value = stmt.value
        return isinstance(value, ast.Constant) and isinstance(value.value, str)
