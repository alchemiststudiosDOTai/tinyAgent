# PLAN.md — Usage Semantics Alignment Rollout (Wait for New `alchemy-llm` Release)

## Status
- **Planning only**.
- **Do not implement yet** in `tinyAgent` until the new crate version is published.
- We already validated the upstream fix exists on `alchemy-rs` master (`4409a50`).

## Goal
Adopt the upstream `alchemy-llm` usage semantics fix so Rust and Python paths in tinyAgent align on provider-raw usage meaning.

## Hard Gate (must be true before any code changes)
- [ ] New `alchemy-llm` crate version is published to crates.io.
- [ ] Release notes/changelog confirm the usage fix includes:
  - provider-raw `input/output`
  - provider `total_tokens` support
  - cache read/write field parsing
  - overflow check update (`input` only, no `+ cache_read`)

---

## Scope of Work (after crate release)

### 1) Dependency upgrade in tinyAgent
Files:
- `Cargo.toml`
- `bindings/alchemy_llm_py/Cargo.toml`

Tasks:
- [ ] Bump `alchemy-llm` from `0.1.1` to `NEW_VERSION` (published version).
- [ ] Refresh lockfile.

Suggested commands:
```bash
cargo update -p alchemy-llm --precise NEW_VERSION
```

### 2) Python provider parity cleanup
File:
- `tinyagent/openrouter_provider.py`

Tasks:
- [ ] Ensure `usage.total_tokens` prefers provider `total_tokens` when present.
- [ ] Keep provider-raw semantics:
  - `input = prompt_tokens`
  - `output = completion_tokens`
  - cache fields from explicit fields, then details fallback

### 3) Contract and regression tests
Files:
- `tests/test_usage_contracts.py`
- (add/adjust focused provider usage tests as needed)

Tasks:
- [ ] Add/adjust tests to assert provider-raw semantics for both paths.
- [ ] Add case where `completion_tokens_details.reasoning_tokens` exists and confirm **not** added to `output`.
- [ ] Add case where provider sends `total_tokens` and confirm we preserve it.
- [ ] Add cache read/write precedence tests.

### 4) Verification runbook (real key-backed)
Tasks:
- [ ] Run Rust path (`stream_alchemy_openai_completions`) live.
- [ ] Run Python path (`stream_openrouter`) live.
- [ ] Save full outputs to `data/` (events + final message).
- [ ] Diff usage semantics and verify expected parity.

Expected outcome:
- Same usage key set and same field meaning across both paths.
- Value differences can still happen due to provider routing/cache state, but semantics must match.

### 5) Docs + changelog
Files:
- `docs/api/caching.md`
- `docs/api/openai-compatible-endpoints.md`
- `CHANGELOG.md`

Tasks:
- [ ] Document provider-raw semantics clearly.
- [ ] Note that `reasoning_tokens` are not folded into `usage.output`.
- [ ] Add release note for semantic alignment.

---

## Execution Checklist (ordered)
1. [ ] Confirm crate release is live.
2. [ ] Create branch for rollout.
3. [ ] Bump Rust dependencies + lockfile.
4. [ ] Apply Python `total_tokens` preference if needed.
5. [ ] Update/add tests.
6. [ ] Run full QA suite.
7. [ ] Run live parity captures.
8. [ ] Update docs/changelog.
9. [ ] Open PR with evidence artifacts in `data/`.

---

## QA Commands (post-implementation)
```bash
uv run pytest -q
uv run pytest -q tests/test_usage_contracts.py -vv
uv run pylint --disable=all --enable=duplicate-code tinyagent
uv run pre-commit run --all-files
```

(Plus Rust/build commands required by the binding path.)

---

## Acceptance Criteria
- [ ] tinyAgent depends on released `alchemy-llm` version containing usage fix.
- [ ] Rust and Python usage semantics are aligned (provider-raw).
- [ ] `output` excludes reasoning-token double-counting.
- [ ] `total_tokens` preserves provider value when present.
- [ ] Cache read/write fields are correctly populated when provider reports them.
- [ ] Test suite + lint + pre-commit pass.
- [ ] Live captures demonstrate contract integrity end-to-end.

---

## Notes
- We are intentionally **not** implementing until crate publish is complete.
- This plan is execution-ready so we can move immediately once release is available.
