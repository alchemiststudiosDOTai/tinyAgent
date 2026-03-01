# Hard Cutover Plan: Type Boundary Cleanup

**Source:** `RESEARCH.md` (2026-03-01)
**Goal:** Eliminate the five root type-system issues with a single hard cutover (no compatibility shims, no dual dict/model runtime paths).

## Cutover Rules (Non-Negotiable)

1. Runtime message/content/event/state models are Pydantic/dataclass models only.
2. No new `TypedDict` runtime models.
3. No dict-style access (`obj["x"]`, `.get()`) on migrated models.
4. `.get()` is allowed only at wire boundaries (SSE/raw JSON/provider payloads).
5. Remove fallback branches that keep old and new paths alive together.

## Scope

This plan addresses all five issues from `RESEARCH.md`:

1. `Model` structure + `getattr()` cascades
2. `AgentEvent` discriminator narrowing gaps
3. `Union[PydanticModel, dict]` message handling
4. Missing serializable protocol (`model_dump` probing)
5. `cast(AgentEvent, ...)` in `EventStream`

## Phase 0: Baseline + Safety Rails

1. Freeze baseline behavior with current tests.
2. Record current grep counts so we can prove removal of unsafe patterns.
3. Confirm `.env` keys are present for live provider smoke tests.

Commands:

```bash
uv run pytest -q
uv run pytest tests/architecture/ -x -q
rg -n "getattr\(model|getattr\(event|isinstance\(msg, dict\)|model_dump\", None\)|cast\(AgentEvent" tinyagent/
```

## Phase 1: Foundation Contract Hard Cutover (Layer 0)

Target file: `tinyagent/agent_types.py`

1. Convert `Model` from dataclass to a Pydantic base model (`_AgentBaseModel`) with explicit serialization support.
2. Define a `ModelDumpable` protocol for objects that implement `model_dump(exclude_none=True)`.
3. Add explicit event narrowing helpers (`TypeGuard` functions) for event subsets used by handlers.
4. Replace `EventStream` queue sentinel typing with a typed queue item union (no `object` fallback).
5. Remove `cast(AgentEvent, ...)` from `EventStream.__anext__`.

Acceptance checks:

```bash
rg -n "cast\(AgentEvent" tinyagent/agent_types.py
rg -n "_WAKEUP_SENTINEL = object\(\)" tinyagent/agent_types.py
```

Both should return no results.

## Phase 2: Provider Serialization Contract (Layers 1-2)

Target files:

- `tinyagent/alchemy_provider.py`
- `tinyagent/proxy.py`

1. Replace ad-hoc `getattr(value, "model_dump", None)` probing with shared protocol-based serializer helper.
2. Standardize serialization error behavior and messages across both providers.
3. Remove dict fallback handling for internal model payloads in migrated paths.
4. Remove `getattr(model, ...)` cascades in `alchemy_provider.py` by using explicit typed model access.

Acceptance checks:

```bash
rg -n "getattr\(model" tinyagent/alchemy_provider.py
rg -n "model_dump\", None\)" tinyagent/alchemy_provider.py tinyagent/proxy.py
```

Both should return no results.

## Phase 3: Message Hard Cutover (Layers 1-3)

Target files:

- `tinyagent/caching.py`
- `tinyagent/agent_loop.py`
- `tinyagent/agent.py`

1. Remove dict branches in caching/message conversion helpers.
2. Make `Context.messages` handling model-only in internal flows.
3. Keep dict parsing only at true wire boundaries.
4. Replace `getattr(event, ...)` and `getattr(msg, ...)` in `agent.py` with TypeGuard-based narrowed access.
5. Update helper functions (for example `extract_text`) to use typed model attributes.

Acceptance checks:

```bash
rg -n "isinstance\(msg, dict\)|isinstance\(message, dict\)|getattr\(event|getattr\(msg" tinyagent/caching.py tinyagent/agent.py tinyagent/agent_loop.py
```

Should return only boundary-safe cases (or nothing).

## Phase 4: Test Refactor + Coverage Additions

Target tests:

- `tests/test_caching.py`
- `tests/test_alchemy_provider.py`
- `tests/test_usage_contracts.py`
- `tests/test_parallel_tool_execution.py`
- `tests/test_agent.py` (and related stream/event tests)

Add/adjust tests for:

1. TypeGuard correctness for all 10 `AgentEvent` variants.
2. `EventStream` behavior after sentinel typing change.
3. Strict serializer protocol behavior in alchemy/proxy providers.
4. Caching transform behavior with model-only message inputs.
5. Regression coverage for tool execution pending set updates and turn-end error capture.

## Phase 5: Live Validation with `.env` Keys

Run live tests after unit/architecture suite is green.

Primary smoke:

```bash
uv run python scripts/smoke_rust_tool_calls_three_providers.py
```

Optional focused smokes:

```bash
uv run python examples/example_chat_alchemy.py
uv run python examples/example_minimax_alchemy.py
uv run python examples/example_tool_calls_three_providers.py
```

Expected result:

1. Streams complete successfully across configured providers.
2. No runtime attribute errors from removed `getattr`/dict branches.
3. Usage contract fields remain present and valid.

## Phase 6: Docs + Release Hygiene

1. Update docs that still describe TypedDict runtime behavior:
   - `docs/api/agent_types.md`
   - `docs/ARCHITECTURE.md`
2. Add changelog entry for hard cutover and migration notes.
3. Document intentional breaking changes in model/event typing expectations.

## Definition of Done

1. All five issues in `RESEARCH.md` are removed in code, not masked.
2. No compatibility shims remain for dict/model dual runtime paths.
3. `uv run pytest -q` passes.
4. `uv run pytest tests/architecture/ -x -q` passes.
5. Live smoke with `.env` provider keys passes.
6. Grep checks confirm removal of unsafe patterns.

## Execution Order (Recommended)

1. `agent_types.py` contracts and EventStream typing
2. provider serialization and model typing (`alchemy_provider.py`, `proxy.py`)
3. message/caching/agent handler cleanup (`caching.py`, `agent_loop.py`, `agent.py`)
4. test updates
5. live smoke and docs/changelog

This order minimizes churn by stabilizing core contracts first, then migrating dependents.
