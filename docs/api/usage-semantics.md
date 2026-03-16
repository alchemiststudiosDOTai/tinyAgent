---
title: Usage Semantics Contract
description: Canonical usage contract for the active built-in provider path.
ontological_relations:
  - extends: providers.md
  - implemented_by: ../../tinyagent/alchemy_provider.py
  - enforced_by: ../../tinyagent/alchemy_provider.py
  - validated_by: ../../tests/test_caching.py
  - validated_by: ../../tests/test_usage_contracts.py
---

# Usage Semantics Contract

## Summary

TinyAgent now uses a single usage contract in the active compatibility path:

- Primary compatibility provider: `stream_alchemy_openai_completions`
  (`tinyagent.alchemy_provider`, backed by the optional external binding)

The keys and meanings are aligned, and binding-backed responses are runtime-validated
before being returned to callers.

## Canonical Usage Shape

Assistant messages expose `AssistantMessage.usage` with this dict shape:

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

Historically, Python and Rust paths were aligned on the same canonical keys. The
current repo keeps the Python-side contract enforcement and compatibility adapter:

- canonical provider-raw key names are enforced in runtime contracts
- provider token meanings are preserved for `input` and `output`
- stable snake_case shape remains (`usage.cost` defaults included)
- binding-backed stream results enforce required usage keys

## Practical Guidance

If you consume `message.usage` downstream:

- treat this schema (`message.usage`) as the source of truth
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
  - Contract checks for canonical usage fields in the current runtime path
  - required `usage` and `usage.cost` keys
  - preservation of usage payload through agent execution

Run:

```bash
.venv/bin/pytest tests/test_caching.py tests/test_usage_contracts.py -q
```
