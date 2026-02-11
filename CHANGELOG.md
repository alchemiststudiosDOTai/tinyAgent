# Changelog

All notable changes to `tiny-agent-os` are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.1.3]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/alchemiststudiosDOTai/tinyAgent/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/alchemiststudiosDOTai/tinyAgent/releases/tag/v0.2.0
