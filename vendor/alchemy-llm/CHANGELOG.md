# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.1.9] - 2026-03-18

### Added
- First-class Kimi provider integration via `Api::AnthropicMessages` and `stream_anthropic_messages` on the shared Anthropic-like runtime
- Built-in Kimi model constructor `kimi_k2_0711_preview()`
- New provider docs: `docs/providers/architecture.md` and `docs/providers/kimi.md`
- Anthropic-style provider work in PR #45 was contributed by `ryumacodes`

### Changed
- README provider status and latest-release metadata now reflect Kimi support
- Kimi provider tests use clearer assertion structure without changing behavior

## [0.1.8] - 2026-03-13

### Added
- First-class z.ai GLM provider integration via `Api::ZaiCompletions` and `stream_zai_completions`
- Built-in z.ai GLM model constructors (`glm_5`, `glm_4_7`, `glm_4_5_*`, `glm_4_32b_0414_128k`)
- New z.ai examples: `examples/zai_glm_simple_chat.rs` and `examples/zai_glm_tool_call_smoke.rs`
- Ast-grep architecture boundary checks under `rules/` with `make ast-rules`
- First-class Featherless provider integration on the shared OpenAI-compatible path
- `featherless_model(...)` helper and `FEATHERLESS_API_KEY` environment lookup

### Changed
- Event stream primitives (`AssistantMessageEventStream`, `EventStreamSender`) are now defined in `src/types/event_stream.rs` and re-exported from `types`
- OpenAI-compatible compatibility detection now recognizes Featherless-specific defaults such as `max_tokens`

## [0.1.7] - 2026-03-05

### Changed
- Deduplicated OpenAI-like provider runtime paths by extracting shared request/stream orchestration and chunk prelude helpers
- Refactored MiniMax and Z.ai providers to use shared stream block handling for interleaved reasoning/content/tool-call sequences
- Reduced duplicate test and type-mapping boilerplate while preserving provider dispatch and enum string round-trip behavior

## [0.1.6] - 2026-02-21

### Fixed
- MiniMax multi-turn streamed tool-call argument assembly no longer drops trailing deltas when chunks interleave tool calls with content/reasoning
- Shared OpenAI-like stream block handling now safely merges id-less MiniMax continuation deltas into the active tool call and ignores orphan arg-only deltas

### Added
- Regression tests for MiniMax interleaved tool-call continuation with both text fallback and `reasoning_details` payloads
- Shared stream parser tests for id-less continuation merge and orphan continuation ignore cases

## [0.1.5] - 2026-02-21

### Added
- First-class `ToolCallId` type in `types`, with serde-transparent serialization and public export
- Cross-provider unified tool-call smoke example: `examples/tool_call_unified_types_smoke.rs`
- Cross-provider smoke runner: `scripts/run_tool_call_unified_types.sh`

### Changed
- `ToolCall.id` now uses `ToolCallId` instead of raw `String`
- `ToolResultMessage.tool_call_id` now uses `ToolCallId` instead of raw `String`
- Transform ID mapping internals now use typed `ToolCallId` keys/values
- Unified tool-call smoke defaults to full typed event + final typed response output

## [0.1.4] - 2026-02-18

### Added
- First-class MiniMax provider via `Api::MinimaxCompletions` and `stream_minimax_completions`
- Built-in MiniMax model constructors for global and CN endpoints
- Live MiniMax examples and smoke scripts for reasoning split, `<think>` fallback, and usage chunks
- New MiniMax provider guide: `docs/providers/minimax.md`
- Documentation index: `docs/README.md`

### Fixed
- MiniMax temperature is clamped to supported range `(0.0, 1.0]`
- Assistant thinking replay preserves `<think>...</think>` wrapping semantics

## [0.1.3] - 2026-02-12

### Fixed
- `openai_completions`: Populate `usage.cost` from OpenRouter/OpenAI-compatible streaming usage payloads (`cost` and `cost_details`)
- `docs`: Fix doctest crate paths to `alchemy_llm` so doctests compile during `cargo test`

## [0.1.2] - 2026-02-12

### Added
- `examples/simple_chat.rs` - Basic chat example using GPT-4o-mini
- `examples/tool_calling.rs` - Tool/function calling demonstration with weather API example

### Fixed
- `openai`: Align usage semantics with provider raw tokens

## [0.1.1] - 2026-02-12

### Added
- Initial crates.io release
- Deployment documentation with crate-publisher skill reference

## [0.1.0] - 2026-02-11

### Added
- Initial release
- Support for 8+ providers: Anthropic, OpenAI, Google, AWS Bedrock, Mistral, xAI, Groq, Cerebras, OpenRouter
- Streaming-first async API
- Type-safe provider abstraction
- Tool calling across providers
- Message transformation for cross-provider compatibility
