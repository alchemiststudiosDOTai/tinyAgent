---
title: "Simple File-Based Prompt Loading – Plan"
phase: Plan
date: "2025-09-23T23:42:00Z"
owner: "Claude Code"
parent_research: "memory-bank/plan/2025-09-23_23-41-57_prompt-handling-system-improvements.md"
git_commit_at_plan: "da6ca1d"
tags: [plan, prompt-handling, file-loading, simple]
---

## Goal
**SINGULAR FOCUS**: Implement a simple, ergonomic file-based prompt loading system that allows users to pass a prompt file path to AI agents and have them use it as the system prompt.

## Scope & Assumptions

### In Scope
- Single prompt file loading (text files only)
- Simple file path resolution
- Direct string replacement for system prompts
- Backward compatibility with existing hardcoded prompts
- Support for both ReactAgent and TinyCodeAgent
- Basic error handling for missing/invalid files

### Out of Scope
- YAML/JSON configuration files
- Environment variable configuration
- Complex prompt template systems
- Multiple prompt loading strategies
- Prompt validation beyond file existence
- Performance optimization or caching
- Advanced error handling and recovery

### Assumptions
- Users want a simple file path → prompt solution
- Text files are sufficient for most use cases
- Backward compatibility is critical
- File system access is available
- Simple error messages are preferred over complex recovery

## Deliverables (DoD)

### Core Functionality
- **File Prompt Loader**: Simple utility to load prompts from text files
- **Agent Constructor Extensions**: Add `prompt_file` parameter to both agents
- **Fallback Mechanism**: Use hardcoded prompts when file loading fails
- **Basic Error Handling**: Clear messages for missing/invalid files

### Documentation
- **API Documentation**: Document new `prompt_file` parameter
- **Usage Example**: Simple demo showing file-based prompt usage
- **README Section**: Brief mention of file-based prompt feature

### Test Coverage
- **Unit Tests**: Test file loading and error handling
- **Integration Tests**: Test agents with custom prompt files
- **Compatibility Tests**: Ensure existing functionality unchanged

## Readiness (DoR)

### Preconditions
- Existing test suite must pass (`pytest tests/api_test/test_agent.py -v`)
- Codebase must be clean (`ruff check . --fix && ruff format .`)
- Git working directory must be clean

### Required Resources
- Access to existing codebase patterns
- Understanding of current agent implementations
- Text file loading capabilities (built into Python)

### Environment Setup
```bash
source .venv/bin/activate
pytest tests/api_test/test_agent.py -v
ruff check . --fix && ruff format .
```

## Milestones

### M1: Basic File Loading (1 day)
- Create simple file loading utility
- Add `prompt_file` parameter to ReactAgent
- Add `prompt_file` parameter to TinyCodeAgent
- Basic error handling for missing files

### M2: Integration & Testing (1 day)
- Integrate file loading with existing prompt system
- Write unit tests for file loading
- Write integration tests for both agents
- Test backward compatibility

### M3: Documentation & Finalization (0.5 day)
- Update API documentation
- Create simple usage example
- Update README with feature mention
- Final testing and validation

## Work Breakdown (Tasks)

### M1: Basic File Loading

#### T101: Create File Loading Utility
- **Summary**: Implement simple utility to load prompts from text files
- **Owner**: Claude Code
- **Estimate**: 2 hours
- **Dependencies**: None
- **Acceptance Tests**:
  - Load prompt from existing text file
  - Handle missing file with clear error
  - Handle empty file gracefully
  - Return file contents as string
- **Files/Interfaces**: `tinyagent/prompt_loader.py`

#### T102: Extend ReactAgent Constructor
- **Summary**: Add `prompt_file` parameter to ReactAgent
- **Owner**: Claude Code
- **Estimate**: 2 hours
- **Dependencies**: T101
- **Acceptance Tests**:
  - Initialize ReactAgent with prompt file
  - Fallback to hardcoded prompt when file missing
  - Maintain backward compatibility
  - Error handling for invalid files
- **Files/Interfaces**: `tinyagent/agents/agent.py`

#### T103: Extend TinyCodeAgent Constructor
- **Summary**: Add `prompt_file` parameter to TinyCodeAgent
- **Owner**: Claude Code
- **Estimate**: 2 hours
- **Dependencies**: T101
- **Acceptance Tests**:
  - Initialize TinyCodeAgent with prompt file
  - Fallback to hardcoded prompt when file missing
  - Maintain existing system_suffix behavior
  - Error handling for invalid files
- **Files/Interfaces**: `tinyagent/agents/code_agent.py`

#### T104: Implement Basic Error Handling
- **Summary**: Add clear error messages for file loading issues
- **Owner**: Claude Code
- **Estimate**: 1 hour
- **Dependencies**: T101, T102, T103
- **Acceptance Tests**:
  - Clear error for missing files
  - Clear error for permission issues
  - Graceful fallback to hardcoded prompts
  - Error logging for debugging
- **Files/Interfaces**: `tinyagent/prompt_loader.py`

### M2: Integration & Testing

#### T201: Write File Loading Unit Tests
- **Summary**: Test the file loading utility with various scenarios
- **Owner**: Claude Code
- **Estimate**: 2 hours
- **Dependencies**: T101
- **Acceptance Tests**:
  - Test successful file loading
  - Test missing file handling
  - Test empty file handling
  - Test permission error handling
- **Files/Interfaces**: `tests/prompt_test/test_file_loader.py`

#### T202: Write ReactAgent Integration Tests
- **Summary**: Test ReactAgent with custom prompt files
- **Owner**: Claude Code
- **Estimate**: 2 hours
- **Dependencies**: T102
- **Acceptance Tests**:
  - Test ReactAgent initialization with prompt file
  - Test tool integration with custom prompts
  - Test fallback to hardcoded prompt
  - Test error scenarios
- **Files/Interfaces**: `tests/prompt_test/test_react_agent.py`

#### T203: Write TinyCodeAgent Integration Tests
- **Summary**: Test TinyCodeAgent with custom prompt files
- **Owner**: Claude Code
- **Estimate**: 2 hours
- **Dependencies**: T103
- **Acceptance Tests**:
  - Test TinyCodeAgent initialization with prompt file
  - Test system_suffix compatibility
  - Test fallback to hardcoded prompt
  - Test error scenarios
- **Files/Interfaces**: `tests/prompt_test/test_code_agent.py`

#### T204: Test Backward Compatibility
- **Summary**: Ensure existing functionality works unchanged
- **Owner**: Claude Code
- **Estimate**: 1 hour
- **Dependencies**: T102, T103
- **Acceptance Tests**:
  - All existing tests pass
  - Default behavior unchanged
  - No breaking changes to public API
- **Files/Interfaces**: `tests/api_test/test_agent.py`

### M3: Documentation & Finalization

#### T301: Update API Documentation
- **Summary**: Document new `prompt_file` parameter
- **Owner**: Claude Code
- **Estimate**: 1 hour
- **Dependencies**: T102, T103
- **Acceptance Tests**:
  - Complete parameter documentation
  - Type hints and examples
  - Error condition documentation
- **Files/Interfaces**: `tinyagent/agents/agent.py`, `tinyagent/agents/code_agent.py`

#### T302: Create Usage Example
- **Summary**: Simple demo showing file-based prompt usage
- **Owner**: Claude Code
- **Estimate**: 1 hour
- **Dependencies**: T102, T103
- **Acceptance Tests**:
  - Working example with ReactAgent
  - Working example with TinyCodeAgent
  - Sample prompt files included
  - Clear instructions for usage
- **Files/Interfaces**: `examples/file_prompt_demo.py`

#### T303: Update README
- **Summary**: Add brief mention of file-based prompt feature
- **Owner**: Claude Code
- **Estimate**: 0.5 hours
- **Dependencies**: T301, T302
- **Acceptance Tests**:
  - README updated with feature description
  - Link to usage example
  - Clear instructions for users
- **Files/Interfaces**: `README.md`

#### T304: Final Validation
- **Summary**: Complete testing and code quality checks
- **Owner**: Claude Code
- **Estimate**: 1 hour
- **Dependencies**: All previous tasks
- **Acceptance Tests**:
  - All tests pass
  - Code quality standards met
  - Documentation complete
  - Feature working as expected
- **Files/Interfaces**: None (validation only)

## Risks & Mitigations

### Risk 1: Breaking Existing Functionality
- **Impact**: High - could break existing user code
- **Likelihood**: Low - changes are additive
- **Mitigation**: Comprehensive backward compatibility testing
- **Trigger**: Any existing test failure

### Risk 2: File Path Security Issues
- **Impact**: Medium - potential directory traversal attacks
- **Likelihood**: Low - simple file loading with basic validation
- **Mitigation**: Basic path validation and error handling
- **Trigger**: Any security test failure

### Risk 3: User Confusion
- **Impact**: Low - users might not understand the feature
- **Likelihood**: Medium - simple feature but needs clear docs
- **Mitigation**: Clear documentation and examples
- **Trigger**: User questions during testing

## Test Strategy

### Unit Testing
- **Coverage**: 100% for new file loading functionality
- **Framework**: pytest with mocking for file operations
- **Focus**: File loading edge cases and error scenarios

### Integration Testing
- **Scope**: End-to-end prompt file usage with both agents
- **Focus**: Agent initialization and custom prompt functionality
- **Environment**: Test fixtures with sample prompt files

### Compatibility Testing
- **Scope**: All existing functionality must work unchanged
- **Method**: Run existing test suite before and after changes
- **Focus**: API backward compatibility and default behavior

## Security & Compliance

### File Security
- Basic file path validation
- No directory traversal protection needed (user-provided paths)
- No sensitive data handling in prompt files

### Input Validation
- Basic file existence checking
- File type validation (text files only)
- Error handling for permission issues

## Observability

### Logging
- File loading events
- Error conditions with context
- Fallback to hardcoded prompts

### Error Handling
- Clear error messages for missing files
- Graceful degradation to hardcoded prompts
- Debug information for troubleshooting

## Rollout Plan

### Environment Order
1. Development environment (current)
2. Test environment with comprehensive test suite
3. Production release (feature is additive and safe)

### Migration Steps
1. Introduce new file loading functionality
2. Maintain existing hardcoded prompts as defaults
3. Provide simple examples and documentation
4. No breaking changes to existing code

### Feature Flags
- No feature flags needed - functionality is additive
- Backward compatibility ensures safe rollout
- Graceful fallback for missing/invalid files

## Validation Gates

### Gate A: Implementation Complete
- File loading utility implemented
- Agent constructors extended
- Basic error handling in place
- Initial unit tests passing

### Gate B: Testing Complete
- All unit tests passing
- Integration tests passing
- Backward compatibility verified
- Error scenarios tested

### Gate C: Documentation Complete
- API documentation updated
- Usage example created and tested
- README updated with feature mention
- All documentation accurate

### Gate D: Quality Assurance
- Code quality standards met (ruff checks)
- All tests passing
- Pre-commit hooks passing
- Feature working as expected

## Success Metrics

### Key Performance Indicators
- **Functionality**: 100% of file loading scenarios work as expected
- **Compatibility**: 0 breaking changes to existing functionality
- **Reliability**: Graceful fallback to hardcoded prompts in all error cases
- **Usability**: Users can easily understand and use the feature

### Quality Benchmarks
- **Test Coverage**: 100% for new functionality
- **Error Handling**: Clear, actionable error messages for all failure modes
- **Performance**: File loading completes in <50ms for typical files
- **Documentation**: Complete examples and API documentation

## References

### Research Document
- `memory-bank/plan/2025-09-23_23-41-57_prompt-handling-system-improvements.md` - Original comprehensive plan

### Key Code Locations
- `tinyagent/prompt.py:1-75` - Current hardcoded prompt templates
- `tinyagent/agents/agent.py:80-85` - ReactAgent prompt initialization
- `tinyagent/agents/code_agent.py:218-220` - TinyCodeAgent prompt initialization
- `tests/api_test/test_agent.py:130-137` - Existing prompt tests

### GitHub Permalinks
- [prompt.py](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/da6ca1d6f6e8b0a6c5e4f3a2b1c9d8e7f6a5b4c3/tinyagent/prompt.py)
- [agent.py](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/da6ca1d6f6e8b0a6c5e4f3a2b1c9d8e7f6a5b4c3/tinyagent/agents/agent.py)
- [code_agent.py](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/da6ca1d6f6e8b0a6c5e4f3a2b1c9d8e7f6a5b4c3/tinyagent/agents/code_agent.py)

## Final Gate

**Plan Summary**: This simplified plan focuses on implementing a straightforward file-based prompt loading system. Users can provide a text file path to agents, which will load and use the file content as the system prompt, with graceful fallback to existing hardcoded prompts.

**Plan Path**: `memory-bank/plan/2025-09-23_23-42-00_simple-file-based-prompt-loading.md`

**Milestones**: 3 milestones spanning 2.5 days total development time

**Validation Gates**: 4 quality gates ensuring implementation, testing, documentation, and quality assurance

**Next Command**: `/execute "/home/fabian/tinyAgent/memory-bank/plan/2025-09-23_23-42-00_simple-file-based-prompt-loading.md"`