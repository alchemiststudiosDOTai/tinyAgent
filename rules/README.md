# rules

AST-grep rules for repository-specific enforcement.

## Python type-shim guard (`TypeAlias` ban)

Rule file:

- `src/rules/ast/rules/no_typealias_python.yml`

Purpose:

- ban `TypeAlias` and `TypeAliasType` shim usage in Python code

Run:

```bash
sg scan --config src/rules/ast/sgconfig.yml --filter no-typealias-python tinyagent tests docs
```

See also:

- `docs/ast-grep-no-typealias.md`

## tinyagent tree hygiene rule

Rule script:

- `scripts/lint_tinyagent_tree.py`

Purpose:

- reject `__pycache__` directories under `tinyagent/`
- reject empty/cache-only directories under `tinyagent/`

Run:

```bash
python3 scripts/lint_tinyagent_tree.py
```

## Harness anti-duck-typing guard

Rule files:

- `rules/harness_no_duck_typing.yml`
- `rules/harness_no_thin_protocols.yml`

Run them only against the harness tree:

```bash
sg scan -r rules/harness_no_duck_typing.yml docs/harness/
sg scan -r rules/harness_no_thin_protocols.yml docs/harness/
```

This enforces in `docs/harness/`:

- no `getattr(...)` on typed values like `event` / `message` / `model`
- no `.get(...)` on those typed values
- no `isinstance(..., dict)` fallback branches on those typed values
- no thin `Protocol` classes in harness code
