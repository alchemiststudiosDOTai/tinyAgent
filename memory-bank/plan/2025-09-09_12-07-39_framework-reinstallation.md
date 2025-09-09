---
title: "Framework Reinstallation After Agent File Movement – Plan"
phase: Plan
date: "2025-09-09 12:07:39"
owner: "Claude"
parent_research: "memory-bank/research/2025-09-09_framework-reinstallation-guide.md"
git_commit_at_plan: "bd3cf3d"
tags: [plan, framework-reinstallation]
---

## Goal
Fix the broken imports after moving agent.py and code_agent.py to tinyagent/agents/ directory by updating all import paths and reinstalling the virtual environment to restore full framework functionality.

## Scope & Assumptions
- **In scope**:
  - Fix all broken imports due to file movement
  - Create missing __init__.py files
  - Update test file imports
  - Reinstall virtual environment
  - Verify all tests pass
- **Out of scope**:
  - Adding new features
  - Changing framework architecture
  - Updating documentation beyond import fixes
- **Assumptions**:
  - Using .venv as virtual environment name
  - UV is available for faster installation
  - No other files were moved during reorganization

## Deliverables (DoD)
1. **tinyagent/agents/__init__.py** - Created with proper exports
2. **Updated tinyagent/__init__.py** - Imports from new locations
3. **Fixed agent files** - Relative imports updated to use ..
4. **Updated test files** - All imports corrected
5. **Fresh virtual environment** - Reinstalled with framework
6. **Passing test suite** - All tests in tests/api_test/ pass
7. **Working examples** - All demo scripts execute successfully

## Readiness (DoR)
- ✅ Agent files moved to tinyagent/agents/
- ✅ Research document completed
- ❌ Missing __init__.py files
- ❌ Broken imports need fixing
- ❌ Virtual environment needs reinstallation

## Milestones
- **M1: Infrastructure Fixes** (30 min) - Create __init__.py files and fix all imports
- **M2: Environment Reinstallation** (15 min) - Remove old venv and create fresh one
- **M3: Verification & Testing** (15 min) - Run tests and examples to confirm functionality

## Work Breakdown (Tasks)

### Task 1.1: Create agents/__init__.py
- **Summary**: Create tinyagent/agents/__init__.py with proper exports
- **Owner**: Claude
- **Estimate**: 5 min
- **Dependencies**: None
- **Target Milestone**: M1
- **Acceptance Tests**:
  - File exists at tinyagent/agents/__init__.py
  - Contains proper imports and exports for ReactAgent and TinyCodeAgent
- **Files/Interfaces**: tinyagent/agents/__init__.py

### Task 1.2: Update tinyagent/__init__.py
- **Summary**: Update main package imports to use new agent locations
- **Owner**: Claude
- **Estimate**: 5 min
- **Dependencies**: Task 1.1
- **Target Milestone**: M1
- **Acceptance Tests**:
  - Imports from .agents.agent and .agents.code_agent
  - All previously exported classes still available
- **Files/Interfaces**: tinyagent/__init__.py

### Task 1.3: Fix agent.py relative imports
- **Summary**: Update relative imports in tinyagent/agents/agent.py
- **Owner**: Claude
- **Estimate**: 5 min
- **Dependencies**: None
- **Target Milestone**: M1
- **Acceptance Tests**:
  - All relative imports use .. instead of .
  - No import errors when importing ReactAgent
- **Files/Interfaces**: tinyagent/agents/agent.py

### Task 1.4: Fix code_agent.py relative imports
- **Summary**: Update relative imports in tinyagent/agents/code_agent.py
- **Owner**: Claude
- **Estimate**: 5 min
- **Dependencies**: None
- **Target Milestone**: M1
- **Acceptance Tests**:
  - All relative imports use .. instead of .
  - No import errors when importing TinyCodeAgent
- **Files/Interfaces**: tinyagent/agents/code_agent.py

### Task 1.5: Update test file imports
- **Summary**: Update imports in all test files to use new paths
- **Owner**: Claude
- **Estimate**: 10 min
- **Dependencies**: Task 1.2
- **Target Milestone**: M1
- **Acceptance Tests**:
  - All test files import successfully
  - pytest discovery works correctly
- **Files/Interfaces**:
  - tests/api_test/test_agent.py
  - tests/api_test/test_code_agent.py
  - tests/api_test/test_agent_advanced.py

### Task 2.1: Remove existing venv
- **Summary**: Completely remove existing virtual environment
- **Owner**: Claude
- **Estimate**: 2 min
- **Dependencies**: All M1 tasks
- **Target Milestone**: M2
- **Acceptance Tests**:
  - .venv directory no longer exists
- **Files/Interfaces**: None (filesystem operation)

### Task 2.2: Create fresh venv and install
- **Summary**: Create new virtual environment and install framework
- **Owner**: Claude
- **Estimate**: 10 min
- **Dependencies**: Task 2.1
- **Target Milestone**: M2
- **Acceptance Tests**:
  - New .venv created successfully
  - Framework installs without errors
  - All dependencies installed
- **Files/Interfaces**: None (environment setup)

### Task 3.1: Verify basic imports
- **Summary**: Test that all main imports work correctly
- **Owner**: Claude
- **Estimate**: 2 min
- **Dependencies**: Task 2.2
- **Target Milestone**: M3
- **Acceptance Tests**:
  - from tinyagent import ReactAgent succeeds
  - from tinyagent import TinyCodeAgent succeeds
- **Files/Interfaces**: Command line verification

### Task 3.2: Run test suite
- **Summary**: Execute all tests to verify functionality
- **Owner**: Claude
- **Estimate**: 5 min
- **Dependencies**: Task 3.1
- **Target Milestone**: M3
- **Acceptance Tests**:
  - All tests in tests/api_test/ pass
  - No test import errors
- **Files/Interfaces**: pytest test runner

### Task 3.3: Test examples
- **Summary**: Run all example scripts to verify end-to-end functionality
- **Owner**: Claude
- **Estimate**: 3 min
- **Dependencies**: Task 3.2
- **Target Milestone**: M3
- **Acceptance Tests**:
  - examples/react_demo.py runs successfully
  - examples/code_demo.py runs successfully
- **Files/Interfaces**: Example scripts

### Task 3.4: Run linting and formatting
- **Summary**: Ensure code quality standards are met
- **Owner**: Claude
- **Estimate**: 2 min
- **Dependencies**: Task 3.3
- **Target Milestone**: M3
- **Acceptance Tests**:
  - ruff check passes
  - ruff format passes
  - pre-commit hooks pass
- **Files/Interfaces**: ruff, pre-commit

## Risks & Mitigations
- **Risk**: Virtual environment name mismatch (.venv vs venv)
  - **Impact**: Medium - Wrong venv might be removed
  - **Likelihood**: Low
  - **Mitigation**: Check which venv exists before removal
  - **Trigger**: If rm command fails
- **Risk**: Missing dependencies in new venv
  - **Impact**: High - Framework won't work
  - **Likelihood**: Low
  - **Mitigation**: Install both main and dev dependencies explicitly
  - **Trigger**: If import errors after installation
- **Risk**: Other files moved during reorganization
  - **Impact**: High - Additional broken imports
  - **Likelihood**: Low
  - **Mitigation**: Search for any other import errors during testing
  - **Trigger**: If unexpected import errors occur

## Test Strategy
- **Unit Tests**: pytest tests/api_test/test_agent.py and test_code_agent.py
- **Integration Tests**: Example scripts execution
- **Smoke Tests**: Basic import verification
- **No Performance Tests**: Not applicable for this fix

## Security & Compliance
- No secret handling required
- No authentication changes
- Standard Python package installation
- No new external dependencies

## Observability
- Standard pytest output for test results
- Ruff linting reports
- Command line verification output

## Rollback Plan
- Git reset to commit bd3cf3d to restore original file structure
- Manual restoration of moved files if needed

## Validation Gates
- **Gate A (Code Fix)**: All imports updated correctly and __init__.py files created
- **Gate B (Installation)**: Virtual environment recreated and framework installed successfully
- **Gate C (Functionality)**: All tests pass and examples work
- **Gate D (Quality)**: Code passes linting and formatting checks

## Success Metrics
- 100% test pass rate
- Zero import errors
- All example scripts execute successfully
- Clean linting report

## References
- Research: memory-bank/research/2025-09-09_framework-reinstallation-guide.md
- Git commit: bd3cf3d
- CLAUDE.md for development workflow

## Agents
- **context-synthesis**: Verify all import paths are updated consistently
- **codebase-analyzer**: Check for any other files that might reference moved agents

## Final Gate
**Plan Path**: memory-bank/plan/2025-09-09_12-07-39_framework-reinstallation.md
**Milestones**: 3 (Infrastructure Fixes, Environment Reinstallation, Verification & Testing)
**Gates**: 4 (Code Fix, Installation, Functionality, Quality)
**Next Command**: `/execute "memory-bank/plan/2025-09-09_12-07-39_framework-reinstallation.md"`
