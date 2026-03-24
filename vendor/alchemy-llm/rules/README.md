# ast-grep rules

Architecture boundary checks for Rust imports.

## Run scan

From repository root:

```bash
sg scan --config rules/sgconfig.yml src --error
```

## Notes

Rules are path-scoped via `files:` globs and intended to run against the repository source tree with `sg scan`.
