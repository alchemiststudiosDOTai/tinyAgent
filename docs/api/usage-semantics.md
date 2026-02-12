---
title: Usage Semantics Contract
description: Canonical usage contract unified across Python and Rust provider paths.
ontological_relations:
  - extends: providers.md
  - implemented_by: ../../tinyagent/openrouter_provider.py
  - enforced_by: ../../tinyagent/alchemy_provider.py
  - validated_by: ../../tests/test_caching.py
  - validated_by: ../../tests/test_usage_contracts.py
---

# Usage Semantics Contract

## Summary

TinyAgent now uses one usage contract across both provider paths:

- Python provider: `stream_openrouter`
- Rust provider: `stream_alchemy_openai_completions` / `stream_alchemy_openrouter`

The keys and meanings are aligned, and Rust path responses are runtime-validated
before being returned to callers.

## Canonical Usage Shape

Assistant messages expose `message["usage"]` with this shape:

```json
{
  "input": 0,
  "output": 0,
  "cache_read": 0,
  "cache_write": 0,
  "total_tokens": 0,
  "cost": {
    "input": 0.0,
    "output": 0.0,
    "cache_read": 0.0,
    "cache_write": 0.0,
    "total": 0.0
  }
}
```

## Field Semantics

| Field | Meaning |
|---|---|
| `input` | Provider-reported prompt/input tokens (`prompt_tokens`) |
| `output` | Provider-reported completion/output tokens (`completion_tokens`) |
| `cache_read` | Cache-hit tokens from provider cache-read fields |
| `cache_write` | Cache-write tokens from provider cache-write fields |
| `total_tokens` | Provider `total_tokens` when present, else `input + output` |
| `cost` | Present for contract stability; currently zero/default values |

Important: reasoning-token detail fields are **not** folded into `output`.

## Provider Field Mapping and Precedence

TinyAgent maps provider usage fields with deterministic precedence:

1. `input` from `prompt_tokens`
2. `output` from `completion_tokens`
3. `cache_read` from:
   - `cache_read_input_tokens` (preferred), else
   - `prompt_tokens_details.cached_tokens`
4. `cache_write` from:
   - `cache_creation_input_tokens` (preferred), else
   - `prompt_tokens_details.cache_write_tokens`
5. `total_tokens` from:
   - `total_tokens` when numeric, else
   - `input + output`

This supports both Anthropic-style cache fields and OpenAI-style nested prompt details.

## What Was Unified

Before alignment, provider paths could disagree on usage interpretation.
After alignment:

- both Python and Rust paths return the same canonical keys
- both paths use provider-raw token meanings for `input` and `output`
- both paths expose stable snake_case keys
- Rust path enforces the contract (`usage` and `usage.cost` required keys)

## Practical Guidance

If you consume `message["usage"]` downstream:

- treat this schema as the source of truth
- use `total_tokens` directly when present
- do not derive custom totals by adding cache fields onto `total_tokens`
- do not assume cache-write stats are always non-zero (some providers omit/inconsistently report)

## Validation Coverage

Contract behavior is covered by:

- `tests/test_caching.py`
  - cache field precedence
  - provider `total_tokens` preference
  - fallback behavior when provider totals are invalid/missing
- `tests/test_usage_contracts.py`
  - Rust/Python boundary contract checks
  - required `usage` and `usage.cost` keys
  - preservation of usage payload through agent execution

Run:

```bash
.venv/bin/pytest tests/test_caching.py tests/test_usage_contracts.py -q
```
