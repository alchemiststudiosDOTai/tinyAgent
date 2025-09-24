---
title: "Prompt Handling System Improvements – Plan"
phase: Plan
date: "2025-09-23T23:41:57Z"
owner: "Claude Code"
parent_research: "memory-bank/research/2025-09-23_prompt-handling-system-analysis.md"
git_commit_at_plan: "ca5c6ea"
tags: [plan, prompt-handling, system-architecture]
---

## Goal
**SINGULAR FOCUS**: Implement a flexible prompt handling system that allows users to customize AI agent prompts through external configuration while maintaining backward compatibility with existing hardcoded prompts.

## Scope & Assumptions

### In Scope
- External prompt file loading (YAML/JSON/Text formats)
- Prompt configuration via environment variables
- Prompt validation and error handling
- Backward compatibility with existing hardcoded prompts
- Extension of ReactAgent and TinyCodeAgent constructors
- Comprehensive test coverage for new functionality

### Out of Scope
- Prompt versioning system (future enhancement)
- Prompt caching mechanisms (performance optimization)
- Dynamic prompt modification at runtime
- Web-based prompt management interface
- AI prompt generation/optimization

### Assumptions
- PyYAML is available for YAML file support
- Users prefer file-based configuration over code modifications
- Existing test patterns should be followed
- Performance impact of file loading is acceptable
- Backward compatibility is critical for adoption

## Deliverables (DoD)

### Core Functionality
- **Prompt Loader**: File-based prompt loading system with YAML/JSON/Text support
- **Configuration Manager**: Environment variable and file path resolution
- **Agent Extensions**: Updated ReactAgent and TinyCodeAgent with prompt customization
- **Validation System**: Prompt format validation and error handling

### Documentation
- **API Documentation**: Complete parameter documentation for new prompt customization options
- **Usage Examples**: Clear examples showing all prompt customization methods
- **Migration Guide**: Instructions for moving from hardcoded to external prompts

### Test Coverage
- **Unit Tests**: 95% coverage for new prompt loading functionality
- **Integration Tests**: End-to-end testing of prompt customization workflows
- **Compatibility Tests**: Ensure existing functionality remains unchanged

### Quality Gates
- **Zero Breaking Changes**: All existing code continues to work unchanged
- **Performance**: <100ms overhead for prompt loading operations
- **Error Handling**: Clear, actionable error messages for all failure modes

## Readiness (DoR)

### Preconditions
- Existing test suite must pass (`pytest tests/api_test/test_agent.py -v`)
- Codebase must be clean (`ruff check . --fix && ruff format .`)
- Git working directory must be clean

### Required Resources
- Access to existing codebase patterns in `tinyagent/prompt.py`
- Understanding of current agent implementations
- PyYAML dependency (already available)

### Environment Setup
```bash
source .venv/bin/activate
pytest tests/api_test/test_agent.py -v
ruff check . --fix && ruff format .
```

## Milestones

### M1: Architecture & Skeleton (2-3 days)
- Design prompt loading architecture
- Create prompt loader skeleton with interface definitions
- Define file format specifications (YAML/JSON/Text)
- Set up test infrastructure for prompt loading

### M2: Core Feature Implementation (3-4 days)
- Implement prompt file loading for all formats
- Add environment variable configuration support
- Extend agent constructors with prompt parameters
- Implement prompt validation and error handling

### M3: Tests & Hardening (2-3 days)
- Comprehensive unit testing for all new functionality
- Integration testing with existing agent workflows
- Performance testing and optimization
- Backward compatibility verification

### M4: Documentation & Examples (1-2 days)
- Update API documentation with new parameters
- Create comprehensive usage examples
- Write migration guide for existing users
- Update README and CLAUDE.md as needed

### M5: Final Validation & Release (1 day)
- End-to-end testing of all prompt customization methods
- Pre-commit hook validation
- Final documentation review
- Release preparation

## Work Breakdown (Tasks)

### M1: Architecture & Skeleton

#### T101: Design Prompt Loading Architecture
- **Summary**: Design the architecture for flexible prompt loading system
- **Owner**: Claude Code
- **Estimate**: 4 hours
- **Dependencies**: None
- **Acceptance Tests**:
  - Architecture diagram created
  - Interface specifications defined
  - File format standards documented
- **Files/Interfaces**: `memory-bank/plan/prompt-architecture.md`

#### T102: Create Prompt Loader Skeleton
- **Summary**: Implement base prompt loader class with interface definitions
- **Owner**: Claude Code
- **Estimate**: 6 hours
- **Dependencies**: T101
- **Acceptance Tests**:
  - Base loader class with abstract methods
  - Type hints and documentation
  - Interface contracts defined
- **Files/Interfaces**: `tinyagent/prompt_loader.py`

#### T103: Define File Format Specifications
- **Summary**: Create specifications for YAML/JSON/Text prompt file formats
- **Owner**: Claude Code
- **Estimate**: 3 hours
- **Dependencies**: T101
- **Acceptance Tests**:
  - YAML schema definition
  - JSON schema definition
  - Text format conventions
- **Files/Interfaces**: `memory-bank/plan/prompt-formats.md`

#### T104: Set Up Test Infrastructure
- **Summary**: Create test framework for prompt loading functionality
- **Owner**: Claude Code
- **Estimate**: 4 hours
- **Dependencies**: T102
- **Acceptance Tests**:
  - Test fixtures for all file formats
  - Mock file system setup
  - Test utility functions
- **Files/Interfaces**: `tests/prompt_test/test_prompt_loader.py`

### M2: Core Feature Implementation

#### T201: Implement YAML Prompt Loading
- **Summary**: Add support for loading prompts from YAML files
- **Owner**: Claude Code
- **Estimate**: 6 hours
- **Dependencies**: T102, T103
- **Acceptance Tests**:
  - Load single prompt from YAML
  - Load multiple prompts from YAML
  - Handle YAML parsing errors
  - Validate YAML structure
- **Files/Interfaces**: `tinyagent/prompt_loader.py`

#### T202: Implement JSON Prompt Loading
- **Summary**: Add support for loading prompts from JSON files
- **Owner**: Claude Code
- **Estimate**: 4 hours
- **Dependencies**: T102, T103
- **Acceptance Tests**:
  - Load single prompt from JSON
  - Load multiple prompts from JSON
  - Handle JSON parsing errors
  - Validate JSON structure
- **Files/Interfaces**: `tinyagent/prompt_loader.py`

#### T203: Implement Text Prompt Loading
- **Summary**: Add support for loading prompts from plain text files
- **Owner**: Claude Code
- **Estimate**: 3 hours
- **Dependencies**: T102, T103
- **Acceptance Tests**:
  - Load prompt from text file
  - Handle file reading errors
  - Handle encoding issues
- **Files/Interfaces**: `tinyagent/prompt_loader.py`

#### T204: Add Environment Variable Configuration
- **Summary**: Implement environment variable support for prompt configuration
- **Owner**: Claude Code
- **Estimate**: 4 hours
- **Dependencies**: T102
- **Acceptance Tests**:
  - Load prompt from environment variable
  - Load prompt file path from environment
  - Handle missing environment variables
  - Validate environment variable values
- **Files/Interfaces**: `tinyagent/prompt_loader.py`

#### T205: Extend ReactAgent Constructor
- **Summary**: Add prompt customization parameters to ReactAgent
- **Owner**: Claude Code
- **Estimate**: 5 hours
- **Dependencies**: T201, T202, T203, T204
- **Acceptance Tests**:
  - Initialize ReactAgent with custom prompt
  - Initialize ReactAgent with prompt file
  - Initialize ReactAgent with environment variable
  - Maintain backward compatibility
- **Files/Interfaces**: `tinyagent/agents/agent.py`

#### T206: Extend TinyCodeAgent Constructor
- **Summary**: Add prompt customization parameters to TinyCodeAgent
- **Owner**: Claude Code
- **Estimate**: 4 hours
- **Dependencies**: T201, T202, T203, T204
- **Acceptance Tests**:
  - Initialize TinyCodeAgent with custom prompt
  - Initialize TinyCodeAgent with prompt file
  - Initialize TinyCodeAgent with environment variable
  - Maintain existing system_suffix behavior
- **Files/Interfaces**: `tinyagent/agents/code_agent.py`

#### T207: Implement Prompt Validation
- **Summary**: Add validation system for prompt formats and content
- **Owner**: Claude Code
- **Estimate**: 4 hours
- **Dependencies**: T201, T202, T203
- **Acceptance Tests**:
  - Validate prompt template variables
  - Validate prompt length limits
  - Validate prompt content safety
  - Provide clear error messages
- **Files/Interfaces**: `tinyagent/prompt_loader.py`

### M3: Tests & Hardening

#### T301: Comprehensive Unit Testing
- **Summary**: Write complete unit tests for all prompt loading functionality
- **Owner**: Claude Code
- **Estimate**: 8 hours
- **Dependencies**: T201, T202, T203, T204, T207
- **Acceptance Tests**:
  - 95% code coverage for new functionality
  - All edge cases covered
  - Error scenarios tested
  - Performance benchmarks established
- **Files/Interfaces**: `tests/prompt_test/test_prompt_loader.py`

#### T302: Integration Testing
- **Summary**: Test prompt loading with existing agent workflows
- **Owner**: Claude Code
- **Estimate**: 6 hours
- **Dependencies**: T205, T206
- **Acceptance Tests**:
  - End-to-end prompt customization workflows
  - Agent initialization with custom prompts
  - Tool integration with custom prompts
  - Error handling in agent context
- **Files/Interfaces**: `tests/prompt_test/test_agent_integration.py`

#### T303: Performance Testing
- **Summary**: Benchmark prompt loading performance and optimize as needed
- **Owner**: Claude Code
- **Estimate**: 4 hours
- **Dependencies**: T201, T202, T203, T204
- **Acceptance Tests**:
  - <100ms loading time for all formats
  - Memory usage within acceptable limits
  - No performance regression for existing functionality
- **Files/Interfaces**: `tests/prompt_test/test_performance.py`

#### T304: Backward Compatibility Verification
- **Summary**: Ensure all existing functionality works unchanged
- **Owner**: Claude Code
- **Estimate**: 4 hours
- **Dependencies**: T205, T206
- **Acceptance Tests**:
  - All existing tests pass
  - Default behavior unchanged
  - No breaking changes to public API
- **Files/Interfaces**: `tests/api_test/test_agent.py`

### M4: Documentation & Examples

#### T401: Update API Documentation
- **Summary**: Document new prompt customization parameters and methods
- **Owner**: Claude Code
- **Estimate**: 4 hours
- **Dependencies**: T205, T206
- **Acceptance Tests**:
  - Complete parameter documentation
  - Type hints and examples
  - Error condition documentation
- **Files/Interfaces**: `tinyagent/agents/agent.py`, `tinyagent/agents/code_agent.py`

#### T402: Create Usage Examples
- **Summary**: Write comprehensive examples showing all prompt customization methods
- **Owner**: Claude Code
- **Estimate**: 4 hours
- **Dependencies**: T205, T206
- **Acceptance Tests**:
  - YAML file usage example
  - JSON file usage example
  - Text file usage example
  - Environment variable usage example
  - Programmatic prompt setting example
- **Files/Interfaces**: `examples/prompt_customization_demo.py`

#### T403: Write Migration Guide
- **Summary**: Create guide for users transitioning from hardcoded prompts
- **Owner**: Claude Code
- **Estimate**: 3 hours
- **Dependencies**: T205, T206
- **Acceptance Tests**:
  - Step-by-step migration instructions
  - Before/after examples
  - Common pitfalls and solutions
- **Files/Interfaces**: `documentation/modules/prompt-migration.md`

#### T404: Update Project Documentation
- **Summary**: Update README and CLAUDE.md with new prompt features
- **Owner**: Claude Code
- **Estimate**: 2 hours
- **Dependencies**: T401, T402
- **Acceptance Tests**:
  - README updated with prompt customization section
  - CLAUDE.md updated with new patterns
  - Feature highlights added
- **Files/Interfaces**: `README.md`, `CLAUDE.md`

### M5: Final Validation & Release

#### T501: End-to-End Testing
- **Summary**: Comprehensive testing of all prompt customization workflows
- **Owner**: Claude Code
- **Estimate**: 4 hours
- **Dependencies**: T402
- **Acceptance Tests**:
  - All usage examples work as documented
  - Error messages are clear and helpful
  - Performance meets requirements
- **Files/Interfaces**: None (validation only)

#### T502: Pre-commit Hook Validation
- **Summary**: Ensure all code quality checks pass
- **Owner**: Claude Code
- **Estimate**: 2 hours
- **Dependencies**: All previous tasks
- **Acceptance Tests**:
  - Ruff checks pass
  - Ruff formatting applied
  - Pre-commit hooks succeed
- **Files/Interfaces**: None (validation only)

#### T503: Final Documentation Review
- **Summary**: Review and finalize all documentation
- **Owner**: Claude Code
- **Estimate**: 2 hours
- **Dependencies**: T401, T402, T403, T404
- **Acceptance Tests**:
  - Documentation accuracy verified
  - Examples tested and working
  - No typos or errors
- **Files/Interfaces**: All documentation files

#### T504: Release Preparation
- **Summary**: Prepare for release with final checks and balances
- **Owner**: Claude Code
- **Estimate**: 2 hours
- **Dependencies**: All previous tasks
- **Acceptance Tests**:
  - Change log updated
  - Version numbers updated if needed
  - Release notes prepared
- **Files/Interfaces**: `CHANGELOG.md`, `setup.py`

## Risks & Mitigations

### Risk 1: Breaking Existing Functionality
- **Impact**: High - could break existing user code
- **Likelihood**: Medium - requires careful API design
- **Mitigation**: Comprehensive backward compatibility testing
- **Trigger**: Any existing test failure or API change

### Risk 2: Performance Degradation
- **Impact**: Medium - could slow agent initialization
- **Likelihood**: Low - file loading is generally fast
- **Mitigation**: Performance benchmarks and optimization
- **Trigger**: Loading times exceed 100ms threshold

### Risk 3: Security Vulnerabilities
- **Impact**: High - prompt injection or file access issues
- **Likelihood**: Low - proper validation can prevent most issues
- **Mitigation**: Input validation and file path sanitization
- **Trigger**: Any security test failure or suspicious behavior

### Risk 4: Complex Configuration Management
- **Impact**: Medium - could confuse users with too many options
- **Likelihood**: Medium - multiple configuration sources possible
- **Mitigation**: Clear documentation and sensible defaults
- **Trigger**: User confusion during beta testing

## Test Strategy

### Unit Testing
- **Coverage**: 95% for all new prompt loading functionality
- **Framework**: pytest with mocking for file operations
- **Focus**: Individual component behavior and edge cases

### Integration Testing
- **Scope**: End-to-end prompt customization workflows
- **Focus**: Agent initialization and prompt resolution
- **Environment**: Test fixtures with sample prompt files

### Performance Testing
- **Metrics**: Loading time, memory usage, CPU utilization
- **Thresholds**: <100ms loading time, minimal memory overhead
- **Tools**: Python timeit, memory_profiler

### Compatibility Testing
- **Scope**: All existing functionality must work unchanged
- **Method**: Run existing test suite before and after changes
- **Focus**: API backward compatibility and default behavior

## Security & Compliance

### Secret Handling
- No secrets stored in prompt files
- Environment variables for sensitive configuration
- Validation of prompt file sources

### Input Validation
- File path sanitization to prevent directory traversal
- Prompt content validation to prevent injection
- File size limits to prevent memory exhaustion

### Threat Model
- File system access restrictions
- Prompt injection prevention
- Configuration validation and sanitization

## Observability

### Metrics
- Prompt loading time
- Prompt cache hit/miss ratios
- Error rates by error type
- Configuration source usage statistics

### Logging
- Prompt file loading events
- Configuration resolution order
- Error conditions with context
- Performance metrics

### Tracing
- Prompt loading request flow
- Configuration resolution sequence
- Error propagation paths

## Rollout Plan

### Environment Order
1. Development environment (current)
2. Test environment with comprehensive test suite
3. Beta release with selected users
4. Production release

### Migration Steps
1. Introduce new prompt loading functionality
2. Maintain existing hardcoded prompts as defaults
3. Provide migration guide and examples
4. Gradually deprecate hardcoded prompts (future)

### Feature Flags
- No feature flags needed - functionality is additive
- Backward compatibility ensures safe rollout
- Graceful degradation for missing/invalid configurations

### Rollback Triggers
- Any breaking change to existing functionality
- Performance degradation beyond acceptable limits
- Security vulnerabilities discovered
- User adoption issues or confusion

## Validation Gates

### Gate A: Design Sign-off
- Architecture review completed
- Interface specifications approved
- File format standards documented
- Test strategy defined

### Gate B: Test Plan Sign-off
- Unit test coverage achieved (95%)
- Integration tests pass
- Performance benchmarks met
- Compatibility verified

### Gate C: Pre-merge Quality Bar
- All existing tests pass
- New functionality fully tested
- Code quality standards met
- Documentation complete

### Gate D: Pre-deploy Checks
- End-to-end testing complete
- Performance validation successful
- Security scan completed
- Documentation review passed

## Success Metrics

### Key Performance Indicators
- **User Adoption**: 50% of active users using custom prompts within 3 months
- **Performance**: <100ms prompt loading time for all formats
- **Reliability**: 99.9% success rate for prompt loading operations
- **Compatibility**: 0 breaking changes to existing functionality

### Service Level Objectives
- **Prompt Loading**: 95% of requests complete in <50ms
- **Error Rate**: <1% of prompt loading operations fail
- **Availability**: 99.9% uptime for prompt loading functionality

### Error Budget
- **Prompt Loading Errors**: Maximum 1% failure rate
- **Performance**: Maximum 5% of requests exceed 100ms threshold
- **Compatibility**: 0 tolerance for breaking changes

## References

### Research Document
- `memory-bank/research/2025-09-23_prompt-handling-system-analysis.md` - Complete analysis of current system and requirements

### Key Code Locations
- `tinyagent/prompt.py:3-27` - System prompt template
- `tinyagent/agents/agent.py:79-85` - ReactAgent prompt initialization
- `tinyagent/agents/code_agent.py:213-216` - TinyCodeAgent prompt initialization
- `tests/api_test/test_agent.py:130-136` - Existing prompt tests

### GitHub Permalinks
- [prompt.py](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/ca5c6ea603a668200672795ddd249061b67e5547/tinyagent/prompt.py)
- [agent.py](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/ca5c6ea603a668200672795ddd249061b67e5547/tinyagent/agents/agent.py)
- [code_agent.py](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/ca5c6ea603a668200672795ddd249061b67e5547/tinyagent/agents/code_agent.py)

### External Dependencies
- **PyYAML**: For YAML file support (already available)
- **Python Standard Library**: json, pathlib, os, sys

## Agents

### context-synthesis Subagent
- **Purpose**: Analyze existing prompt handling patterns and user requirements
- **Scope**: Review current implementation, identify improvement opportunities, validate research findings

### codebase-analyzer Subagent
- **Purpose**: Detailed analysis of existing agent implementations and prompt usage
- **Scope**: Examine ReactAgent and TinyCodeAgent prompt initialization, understand current patterns, identify extension points

## Final Gate

**Plan Summary**: This execution-ready plan provides a comprehensive roadmap for implementing a flexible prompt handling system in tinyagent. The plan includes 25+ detailed tasks organized across 5 milestones, with clear acceptance criteria, deliverables, and validation gates. The implementation maintains full backward compatibility while adding extensive prompt customization capabilities.

**Plan Path**: `memory-bank/plan/2025-09-23_23-41-57_prompt-handling-system-improvements.md`

**Milestones**: 5 milestones spanning 8-13 days total development time

**Validation Gates**: 4 quality gates ensuring design, testing, code quality, and deployment readiness

**Next Command**: `/execute "/home/fabian/tinyAgent/memory-bank/plan/2025-09-23_23-41-57_prompt-handling-system-improvements.md"`