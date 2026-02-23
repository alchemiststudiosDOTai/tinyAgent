# Changelog

All notable changes to `tiny-agent-os` are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.2.4...HEAD
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
