# Changelog

All notable changes to tinyAgent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial CHANGELOG.md setup

## [0.73.3] - 2025-10-01

### Changed
- **BREAKING**: Restructured core modules for better organization
  - `tinyagent/agent.py` → `tinyagent/agents/react.py`
  - `tinyagent/code_agent.py` → `tinyagent/agents/code.py`
  - Created `core/`, `prompts/`, and `tools/` directories
  - Updated all import statements to use new module paths
  - Public API remains unchanged: `from tinyagent import ReactAgent, TinyCodeAgent, tool`

### Added
- File-based prompt loading system for both ReactAgent and TinyCodeAgent
  - Support for `.txt`, `.md`, `.prompt`, and `.xml` file extensions
  - Graceful fallback to default prompts if files are missing or invalid
  - Easy customization using `prompt_file` parameter
- Comprehensive final answer logic across both agents
  - New `Finalizer` class for unified final answer handling
  - `RunResult` return type for detailed execution tracking
  - Custom exceptions: `StepLimitReached`, `MultipleFinalAnswers`, `InvalidFinalAnswer`
- Security improvements with Bandit integration in pre-commit hooks
- Jina Reader demo example with optional API key support
- Agent comparison documentation with feature matrix and migration examples
- One-page tools guide for quick reference

### Fixed
- Package name updated to match PyPI (`tiny-agent-os`)
- Test registry variable name consistency (`_REGISTRY` → `REGISTRY`)
- Setuptools include-package-data configuration
- Import paths in test files after agent file movement

### Security
- Added Bandit static analysis to pre-commit hooks
- Suppressed false positives for urllib B310 and exec B102 warnings

## [0.73.2] - 2025-09-09

### Fixed
- Framework reinstallation after agent file movement
- Updated patch decorators to use correct module paths in tests
- Moved development dependencies to main dependencies for better availability

### Changed
- Reorganized documentation structure
- Improved project packaging configuration

## [0.73.1] - 2025-09-08

### Fixed
- Registry variable name in test_code_agent.py

## [0.73.0] - 2025-09-01

### Added
- Initial release of restructured tinyAgent framework
- ReactAgent and TinyCodeAgent with unified tool registration
- Core module organization with types, exceptions, and registry
- Built-in web search capabilities
- Comprehensive test suite with 53+ tests passing

---

## Changelog Maintenance

This changelog is maintained in the `.changelog/` directory to keep it separate from the main codebase while ensuring it's tracked in version control.

For detailed development history and commit messages, refer to the git repository:
```bash
git log --oneline --since="1 month ago"
```
