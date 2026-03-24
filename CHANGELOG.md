# Changelog

All notable changes to `tiny-agent-os` are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

## [1.2.23] - 2026-03-24

### Fixed
- Fixed the Linux release workflow import check by replacing the inline `python -c` command with a heredoc so shell quoting cannot strip `"tinyagent"` from `sys.path.insert(...)`.

## [1.2.22] - 2026-03-24

### Fixed
- Fixed Linux wheel builds by moving the manylinux Docker build from `manylinux2014` (OpenSSL 1.0.2) to `manylinux_2_28`, which satisfies the `openssl-sys` minimum supported OpenSSL version.

## [1.2.21] - 2026-03-24

### Fixed
- Fixed Linux manylinux wheel builds by disabling vendored-OpenSSL-from-source (use system OpenSSL + auditwheel repair to avoid CI Perl module dependency churn).

## [1.2.20] - 2026-03-24

### Fixed
- Fixed Linux wheel builds by installing the missing Perl `IPC::Cmd` module dependency required for the vendored OpenSSL compile in manylinux.
- Fixed macOS/Windows wheel builds by validating the staged `_alchemy` binary without importing `tinyagent/__init__.py` (avoids missing runtime deps like `pydantic` in CI).

## [1.2.19] - 2026-03-24

### Fixed
- Fixed Linux wheel builds in CI by running the manylinux build inside Docker (avoids Node/glibc mismatch from job-level containers).
- Fixed macOS Rust binding builds by enabling the `-undefined dynamic_lookup` link args so pyo3 can resolve Python symbols at runtime on arm64.

## [1.2.18] - 2026-03-24

### Added
- Restored the Rust `_alchemy` binding in-repo and added a typed Python adapter for it.
- Added a new PyPI publish workflow that builds the binding per platform and uploads the resulting wheels.
- The release workflow now uploads a `.artifact` debug bundle per platform with wheel metadata and staged-binding state for CI triage.

### Fixed
- Avoided system OpenSSL dependencies in Linux wheel builds by switching the TLS stack to a vendored build.

## [1.2.17] - 2026-03-23

### Fixed
- Repaired Linux release wheels with `auditwheel` in CI so published artifacts use PyPI-compatible `manylinux` tags instead of generic `linux_x86_64`.
- Added a release-wheel tag check that blocks generic Linux wheel tags before smoke test and publish.
- Updated the release docs and harness guidance to document the repaired Linux wheel path and the new wheel-tag gate.

## [1.2.16] - 2026-03-23

### Fixed
- Added Linux to the release workflow matrix so tag/manual releases now build and publish Linux, macOS, and Windows wheels with the staged `tinyagent._alchemy` binding.
- Switched PyPI publishing in the release workflow to the repository `PYPI_TOKEN` secret while keeping GitHub release asset uploads enabled for the same artifacts.
- Clarified release docs and harness notes so the published release path explicitly covers GitHub release assets and PyPI uploads for all three platforms.

## [1.2.15] - 2026-03-22

### Fixed
- Pinned the Windows release workflow to `C:\Strawberry\perl\bin\perl.exe` via `OPENSSL_SRC_PERL` and `PERL`, so vendored `openssl-src` no longer depends on runner `PATH` ordering during the external binding build.
- Corrected the release guidance to document the verified external wheel layout (`_alchemy/_alchemy...`) and the current staging contract.

## [1.2.14] - 2026-03-22

### Fixed
- Accepted the actual external binding wheel package layout (`_alchemy/_alchemy...`) when staging release artifacts, which unblocks the macOS release job after the 1.2.13 hotfix still proved too narrow.

## [1.2.13] - 2026-03-22

### Fixed
- Accepted both `tinyagent/_alchemy...` and top-level `_alchemy...` wheel layouts when staging the external binding for release packaging, so the macOS release job can consume the built binding wheel.
- Switched the Windows release job to Strawberry Perl before building the vendored OpenSSL dependency, avoiding the broken runner Perl that blocked the wheel build.

## [1.2.12] - 2026-03-22

### Added
- Added `examples/minimax_tool_contract_examples.py` back as the runnable/property-tested MiniMax contract example module consumed by the test suite.
- Added `.github/workflows/release-platform-wheels.yml` to build and publish macOS and Windows wheels with the staged external `tinyagent._alchemy` binding.

### Fixed
- Restored the missing MiniMax example module so the hypothesis-based contract test suite collects and passes again.
- Improved optional alchemy-binding import failures to preserve the original loader error, making release-time binding mismatches diagnosable.
- Hardened the release binding check to reject staged `_alchemy` binaries that do not match the host platform format before packaging.
- Tagged staged-binding Linux wheels as `cp310-abi3` instead of interpreter-specific `cp310-cp310`, so the release wheel installs correctly across supported CPython versions.

### Docs
- Added the dedicated MiniMax single-tool example page and documented the staged-binding release workflow for cross-platform wheels.

## [1.2.11] - 2026-03-17

### Fixed
- Restored `Agent.replace_messages(...)` and `Agent.append_message(...)` after their accidental removal in `1.2.10`, preserving minor-version source compatibility for downstream integrations.
- Re-aligned the `tinyagent` package layout and behavior with the pre-regression public API contract used by existing users.

## [1.2.10] - 2026-03-17

### Changed
- Refactored `Agent` runtime internals by extracting streaming, event handling, and configuration into separate modules (`agent_streaming.py`, `agent_event_handler.py`, `agent_options.py`, `message_content.py`).
- Updated ARCHITECTURE.md to reflect new module boundaries and responsibilities.
- Configured setuptools to include staged prebuilt `tinyagent._alchemy` extension artifacts in release wheels again when those binaries are copied into `tinyagent/` from the external binding repo.

### Added
- `scripts/check_release_binding.py` - release gate for the `_alchemy` wheel contract, plus tests covering package-data and staged-binary checks.
- `HARNESS.md` - Critical enforcement document describing pre-commit hooks, ratchets, and rule entry points.
- `py-compile` pre-commit hook to catch syntax and import-time compilation errors.
- `tinyagent-file-length` pre-commit hook with 400-line ratchet for files under `tinyagent/`.
- `docs/harness/HARNESS.md` - Guardrails for code in `docs/harness`.

### Docs
- Updated `AGENTS.md` to reference `HARNESS.md` and document enforcement-first policy.
- Removed obsolete API entries from `docs/api/agent.md` (replaced by typed `AgentOptions`).

## [1.2.9] - 2026-03-16

### Fixed
- Added a fallback import path for the optional external alchemy binding so TinyAgent accepts both `tinyagent._alchemy` and top-level `_alchemy` wheel layouts after the repo split.

## [1.2.8] - 2026-03-16

### Added
- Added `tinyagent/py.typed` to mark the published Python package as typed.

### Changed
- Switched the repo build from a local `maturin` mixed Rust/Python package to a pure Python `setuptools` build.
- Reframed `tinyagent/alchemy_provider.py` as a compatibility adapter for the optional external binding repo at `https://github.com/tunahorse/tinyagent-alchemy`.
- Updated README, API docs, architecture notes, harness guidance, and `AGENTS.md` to treat the Rust binding as external to this repo.

### Fixed
- Skipped the live harness test when provider API keys are not configured so the default test suite stays green in clean environments.

### Removed
- Removed the in-repo Rust binding manifests and local binding-enforcement lint now that binding ownership has moved out of this repository.
- Removed stale binding-specific docs and diagrams that still described `src/lib.rs` as the source of truth.

## [1.2.7] - 2026-03-04

### Added
- Added an AST-grep `no_any_python` rule with tests and snapshots under `src/rules/ast/` to enforce the TypedDict-to-Pydantic hard cutover policy.
- Added an opt-in live integration test at `tests/test_tool_call_types_harness.py` for end-to-end harness validation (`RUN_LIVE_HARNESS=1`).

### Changed
- Tightened `tinyagent/alchemy_provider.py` stream boundary typing by replacing `Any` with protocol/object-typed interfaces.
- Extended `docs/harness/tool_call_types_harness.py` provider resolution to include MiniMax and switched tool args to `JsonObject` with numeric coercion.

## [1.2.6] - 2026-03-03

### Added
- Added a mandatory live type-contract harness at `docs/harness/tool_call_types_harness.py` to verify one real tool-call turn and print model/event type names.
- Added regression tests for strict model serialization boundaries and malformed proxy event handling.

### Changed
- Completed the hard cutover to strict model/event contracts in core runtime paths (agent loop, tool execution, caching, proxy handling, and provider serialization).
- Removed the legacy `openrouter_provider` path in favor of the Rust-backed OpenAI-compatible provider flow.

### Fixed
- Restored provider env-key fallback for `openrouter` (`OPENROUTER_API_KEY`) in `tinyagent/alchemy_provider.py`.
- Hardened proxy streaming event handling by clamping malformed/negative `contentIndex` values.
- Improved cross-provider tool-call smoke examples to preserve tool execution error signals.

### Docs
- Updated architecture/API/hard-cutover documentation to reflect strict model-only contracts and the new harness location.

## [1.2.5] - 2026-02-23

### Added
- Executed tool-call batches in parallel via `asyncio.gather()` in `execute_tool_calls()`.
- Added `examples/example_parallel_tools.py` to compare parallel vs sequential tool execution behavior and timing.

### Changed
- In parallel mode, steering is now applied after the full tool batch completes; already-started tool calls are no longer skipped mid-batch.
- Tool execution events now follow a batch lifecycle: emit all `tool_execution_start` events first, then emit ordered `tool_execution_end` and tool-result message events.

### Fixed
- Propagated task-level cancellation during parallel tool execution instead of converting it into a synthetic tool error.
- Prevented a self-cancelled tool from aborting the entire parallel tool batch.
- Removed duplicate steering polling after tool batches in the agent loop.
- Hardened Rust tool-call argument normalization to only accept JSON objects (non-object payloads now normalize to `{}`).
- Switched tool-result timestamps to `asyncio.get_running_loop()` for async-loop-safe timing.

### Docs
- Aligned steering/interruption docs to the post-batch parallel execution contract across architecture and API pages.

### Tests
- Added comprehensive coverage for parallel tool execution order, concurrency, per-tool error isolation, and cancellation behavior.
- Added regression coverage for task cancellation propagation in `execute_tool_calls()`.
- Added loop-level coverage to ensure steering is not double-polled after a tool batch.
- Added Rust unit coverage for strict tool-call argument normalization.

## [1.2.4] - 2026-02-21

### Fixed
- Upgraded `alchemy-llm` 0.1.5 -> 0.1.6: fixes MiniMax multi-turn tool call arguments (turn 2+ no longer send `{}`).
- Normalized tool call arguments in Rust binding and Python fallback.

### Added
- Added `scripts/smoke_rust_tool_calls_three_providers.py` as the canonical raw Rust-binding multi-turn tool-call smoke script (OpenRouter, MiniMax, Chutes).

### Changed
- Default Chutes model in the Rust smoke script is now `Qwen/Qwen3-Coder-Next-TEE` (override with `CHUTES_MODEL`).

## [1.2.3] - 2026-02-21

### Changed
- Upgraded Rust dependency to `alchemy-llm` `0.1.5`.
- Updated the PyO3 binding bridge to map tool call IDs into alchemy's typed `ToolCallId` fields for both assistant tool calls and tool results.

### Added
- Added `examples/example_tool_calls_three_providers.py` for one-agent tool-call smoke runs across OpenRouter, MiniMax, and Chutes.

### Docs
- Added explicit cross-provider smoke-run output documentation for Rust-backed tool calls in `docs/api/providers.md`.
- Added a quick pointer to the three-provider tool-call example in `docs/README.md`.

## [1.2.1] - 2026-02-18

### Fixed
- Prevented an extra agent turn when tool execution returns no tool results.
- Updated examples to import `Agent` through the package public API.

### Tests
- Added regression coverage to ensure `Agent.prompt()` does not re-enter the stream loop after empty tool execution results.


## [1.2.0] - 2026-02-17

### Added
- Reasoning effort levels support in Alchemy provider (`low`, `medium`, `high`)
- `ThinkingContent` type for reasoning/thinking blocks with `cache_control` support

### Docs
- Documented reasoning effort levels and ThinkingContent usage
- Added example demonstrating reasoning vs text block separation

### Fixed
- Use absolute URL for logo in README

## [1.1.5] - 2026-02-12

### Changed
- Upgraded Rust dependency to `alchemy-llm` `0.1.3`.
- Aligned usage semantics with provider-raw reporting across Python and Rust paths.
- OpenRouter usage normalization now prefers provider `total_tokens` when present.
- Rust OpenAI-compatible stream path now maps OpenRouter cost fields into `usage.cost`.

### Tests
- Expanded usage normalization tests for provider `total_tokens`, cache precedence, and nested cache-write details.
- Added Rust-side cost mapping coverage for `cost`, `cost_details`, and fallback behavior.

### Docs
- Updated caching and OpenAI-compatible endpoint docs to use snake_case usage keys and document provider-raw semantics.

## [1.1.3] - 2026-02-11

### Added
- OpenAI-compatible `base_url` support across Python and Rust providers
- Runtime type contract tests

### Changed
- Expanded OpenAI-compatible endpoint guidance for Rust and Chutes

## [1.1.2] - 2026-02-10

### Added
- Raw usage aliases (`prompt_tokens`, `completion_tokens`) for downstream compatibility

## [1.1.1] - 2026-02-09

### Added
- Prompt caching pipeline: `cache_control` field on `TextContent` and `ThinkingContent`
- `add_cache_breakpoints()` transform with `enable_prompt_caching` option
- OpenRouter structured content blocks and `anthropic-beta` header support
- Cache usage stats parsing from API responses
- Verification tests for prompt caching pipeline

### Fixed
- OpenRouter prompt caching behavior and documentation
- Alchemy provider import and typing issues

### Removed
- Unused `_annotate_system_prompt_block`
- `add_cache_breakpoints` re-export from package root

## [1.1.0] - 2026-02-08

### Changed
- Switched to PyO3 abi3 stable ABI for broader Python version compatibility
- Added vendored OpenSSL for Linux cross-compilation

## [1.0.0] - 2026-02-08

### Changed
- Restructured as maturin mixed Python/Rust build

## [0.2.0] - 2026-02-08

### Added
- Initial PyPI release
- Maturin mixed Python/Rust project structure
- grimp-based import boundary enforcement as pre-commit hook
- Code quality gates (dead code, duplicates, debt)
- Rust `alchemy_llm_py` binding documentation

[Unreleased]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.16...HEAD
[1.2.16]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.15...v1.2.16
[1.2.15]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.14...v1.2.15
[1.2.14]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.13...v1.2.14
[1.2.13]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.12...v1.2.13
[1.2.12]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.11...v1.2.12
[1.2.11]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.10...v1.2.11
[1.2.10]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.9...v1.2.10
[1.2.9]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.8...v1.2.9
[1.2.8]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.7...v1.2.8
[1.2.7]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.6...v1.2.7
[1.2.6]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.5...v1.2.6
[1.2.5]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.4...v1.2.5
[1.2.4]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.3...v1.2.4
[1.2.3]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.1.5...v1.2.0
[1.1.5]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.1.4...v1.1.5
[1.1.3]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/alchemiststudiosDOTai/tinyAgent/releases/tag/v0.2.0
