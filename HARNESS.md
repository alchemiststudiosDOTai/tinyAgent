# HARNESS.md

This document defines guardrails for code in `docs/harness/`.

## Purpose

`docs/harness/` is our live cutover proof path. It should stay strict, minimal, and model-first.

When we find a bug pattern or type-safety gap, we should prevent regressions by adding **code-level rules** (not just comments or tribal knowledge).

## Current code-level rules

Rule files live in `rules/`:

- `rules/harness_no_duck_typing.yml`
- `rules/harness_no_thin_protocols.yml`

These enforce in `docs/harness/`:

1. No `getattr(...)` on typed runtime values like `event`, `message`, `model`, etc.
2. No `.get(...)` on those typed runtime values.
3. No `isinstance(..., dict)` fallback branches for those typed runtime values.
4. No thin duck-typing `Protocol` classes.

## Run the rules

```bash
sg scan -r rules/harness_no_duck_typing.yml docs/harness/
sg scan -r rules/harness_no_thin_protocols.yml docs/harness/
```

## Regression prevention policy

As we run into issues or learn new failure modes, we should:

1. Fix the code path.
2. Add or tighten a rule so the same class of bug cannot re-enter.
3. Keep the rule scoped and explicit (prefer narrow, high-signal checks).
4. Re-run rule scans on `docs/harness/` and keep them clean.

In short: **every important lesson should become an enforceable guardrail.**
