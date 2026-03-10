# AST Rule: No `TypeAlias` / `TypeAliasType` Shims

This repository enforces a strict rule to prevent `TypeAlias`-based shim types in Python.

Rule file:

- `src/rules/ast/rules/no_typealias_python.yml`

## Why

`TypeAlias` and `TypeAliasType` can become an abstraction layer that hides real concrete types.
For this codebase, we prefer direct, explicit types over alias shims.

## What is banned

The rule flags these symbols anywhere in scoped Python files:

- `TypeAlias`
- `typing.TypeAlias`
- `typing_extensions.TypeAlias`
- `TypeAliasType`
- `typing_extensions.TypeAliasType`

## Scope

The rule currently scans:

- `tinyagent/**/*.py`
- `tests/**/*.py`
- `docs/**/*.py`

## Run locally

From repo root:

```bash
sg scan --config src/rules/ast/sgconfig.yml --filter no-typealias-python tinyagent tests docs
sg test --config src/rules/ast/sgconfig.yml
```

## Notes

- This is a structural lint rule (ast-grep), not a runtime check.
- If you need shared typing structure, use concrete generic types directly in-place instead of alias shims.
