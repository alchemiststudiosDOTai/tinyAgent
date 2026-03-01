# rules

AST-grep rules for repository-specific enforcement.

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
