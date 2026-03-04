# AST Rules

ast-grep rules for source code enforcement.

Current rules:

- `rules/no_any_python.yml`: absolute ban on `Any` in Python type annotations and imports.

Run from repository root:

```bash
sg scan --config src/rules/ast/sgconfig.yml
sg test --config src/rules/ast/sgconfig.yml
```
